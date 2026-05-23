// SPDX-License-Identifier: GPL-2.0
/*
 * unicell.c — Linux kernel driver for Imago-UniCell PCIe accelerator
 *
 * Exposes /dev/unicell0 with ioctl interface for:
 *   - Configuring cells (command, topology)
 *   - Injecting packets (A preload, B trigger)
 *   - Reading cell output and status
 *
 * BAR0 layout (CELL_STRIDE=32 bytes per cell):
 *   offset 0x00  command     (W)
 *   offset 0x04  topology    (W)
 *   offset 0x08  a_data      (W)
 *   offset 0x0C  b_inject    (W) — triggers computation
 *   offset 0x10  output      (R)
 *   offset 0x14  status      (R) — bit0=a_arrived, bit1=output_valid
 *   offset 0x18  reserved
 *   offset 0x1C  reserved
 *
 * Build:
 *   make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
 *
 * Load:
 *   sudo insmod unicell.ko
 *   ls /dev/unicell0
 */

#include <linux/module.h>
#include <linux/pci.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/uaccess.h>
#include <linux/io.h>
#include <linux/mutex.h>

#define DRIVER_NAME     "unicell"
#define UNICELL_VENDOR  0x10EE   /* Xilinx/AMD vendor ID — LitePCIe default */
#define UNICELL_DEVICE  0x7021   /* LitePCIe 7-series Gen2 default device ID */

#define CELL_STRIDE     32       /* bytes per cell in BAR0 */
#define MAX_CELLS       1024

/* Register offsets within each cell's CELL_STRIDE block */
#define REG_COMMAND     0x00
#define REG_TOPOLOGY    0x04
#define REG_A_DATA      0x08
#define REG_B_INJECT    0x0C
#define REG_OUTPUT      0x10
#define REG_STATUS      0x14

/* ioctl definitions */
#define UNICELL_IOC_MAGIC  'U'

struct unicell_cell_cmd {
    __u32 cell_index;
    __u32 command;    /* cell command word (topology, one_shot, loop, etc.) */
    __u32 topology;   /* topology word */
    __u32 a_data;     /* preloaded A value */
};

struct unicell_inject {
    __u32 cell_index;
    __u32 b_data;     /* B packet data to inject */
};

struct unicell_read {
    __u32 cell_index;
    __u32 output;     /* returned output value */
    __u32 status;     /* returned status flags */
};

struct unicell_info {
    __u32 num_cells;
    __u32 bar0_size;
    __u32 vendor_id;
    __u32 device_id;
};

#define UNICELL_IOCTL_CONFIGURE  _IOW(UNICELL_IOC_MAGIC, 1, struct unicell_cell_cmd)
#define UNICELL_IOCTL_INJECT     _IOW(UNICELL_IOC_MAGIC, 2, struct unicell_inject)
#define UNICELL_IOCTL_READ       _IOWR(UNICELL_IOC_MAGIC, 3, struct unicell_read)
#define UNICELL_IOCTL_RESET      _IO(UNICELL_IOC_MAGIC,  4)
#define UNICELL_IOCTL_INFO       _IOR(UNICELL_IOC_MAGIC, 5, struct unicell_info)

/* Device state */
struct unicell_dev {
    struct pci_dev  *pdev;
    void __iomem    *bar0;
    resource_size_t  bar0_size;
    u32              num_cells;
    struct cdev      cdev;
    struct device   *device;
    struct mutex     lock;
};

static struct unicell_dev *g_udev;
static dev_t               unicell_devt;
static struct class       *unicell_class;

/* BAR0 accessors */
static inline void cell_write(struct unicell_dev *dev, u32 cell, u32 reg, u32 val)
{
    iowrite32(val, dev->bar0 + cell * CELL_STRIDE + reg);
}

static inline u32 cell_read(struct unicell_dev *dev, u32 cell, u32 reg)
{
    return ioread32(dev->bar0 + cell * CELL_STRIDE + reg);
}

/* File operations */
static int unicell_open(struct inode *inode, struct file *file)
{
    file->private_data = g_udev;
    return 0;
}

static int unicell_release(struct inode *inode, struct file *file)
{
    return 0;
}

static long unicell_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
    struct unicell_dev *dev = file->private_data;
    int ret = 0;

    mutex_lock(&dev->lock);

    switch (cmd) {

    case UNICELL_IOCTL_CONFIGURE: {
        struct unicell_cell_cmd c;
        if (copy_from_user(&c, (void __user *)arg, sizeof(c))) {
            ret = -EFAULT; break;
        }
        if (c.cell_index >= dev->num_cells) {
            ret = -EINVAL; break;
        }
        /* Write command registers — freeze implied by driver serialisation */
        cell_write(dev, c.cell_index, REG_COMMAND,  c.command);
        cell_write(dev, c.cell_index, REG_TOPOLOGY, c.topology);
        cell_write(dev, c.cell_index, REG_A_DATA,   c.a_data);
        break;
    }

    case UNICELL_IOCTL_INJECT: {
        struct unicell_inject inj;
        if (copy_from_user(&inj, (void __user *)arg, sizeof(inj))) {
            ret = -EFAULT; break;
        }
        if (inj.cell_index >= dev->num_cells) {
            ret = -EINVAL; break;
        }
        /* Writing b_inject fires the B arrival — triggers gate computation */
        cell_write(dev, inj.cell_index, REG_B_INJECT, inj.b_data);
        break;
    }

    case UNICELL_IOCTL_READ: {
        struct unicell_read rd;
        if (copy_from_user(&rd, (void __user *)arg, sizeof(rd))) {
            ret = -EFAULT; break;
        }
        if (rd.cell_index >= dev->num_cells) {
            ret = -EINVAL; break;
        }
        rd.output = cell_read(dev, rd.cell_index, REG_OUTPUT);
        rd.status = cell_read(dev, rd.cell_index, REG_STATUS);
        if (copy_to_user((void __user *)arg, &rd, sizeof(rd)))
            ret = -EFAULT;
        break;
    }

    case UNICELL_IOCTL_RESET: {
        /* Write 0 to command of all cells — safe reset */
        u32 i;
        for (i = 0; i < dev->num_cells; i++)
            cell_write(dev, i, REG_COMMAND, 0);
        break;
    }

    case UNICELL_IOCTL_INFO: {
        struct unicell_info info = {
            .num_cells = dev->num_cells,
            .bar0_size = (u32)dev->bar0_size,
            .vendor_id = dev->pdev->vendor,
            .device_id = dev->pdev->device,
        };
        if (copy_to_user((void __user *)arg, &info, sizeof(info)))
            ret = -EFAULT;
        break;
    }

    default:
        ret = -ENOTTY;
    }

    mutex_unlock(&dev->lock);
    return ret;
}

static const struct file_operations unicell_fops = {
    .owner          = THIS_MODULE,
    .open           = unicell_open,
    .release        = unicell_release,
    .unlocked_ioctl = unicell_ioctl,
};

/* PCI probe */
static int unicell_probe(struct pci_dev *pdev, const struct pci_device_id *id)
{
    struct unicell_dev *udev;
    int ret;

    udev = devm_kzalloc(&pdev->dev, sizeof(*udev), GFP_KERNEL);
    if (!udev)
        return -ENOMEM;

    udev->pdev = pdev;
    mutex_init(&udev->lock);

    ret = pcim_enable_device(pdev);
    if (ret) {
        dev_err(&pdev->dev, "Failed to enable PCI device\n");
        return ret;
    }

    pci_set_master(pdev);

    ret = pcim_iomap_regions(pdev, BIT(0), DRIVER_NAME);
    if (ret) {
        dev_err(&pdev->dev, "Failed to map BAR0\n");
        return ret;
    }

    udev->bar0      = pcim_iomap_table(pdev)[0];
    udev->bar0_size = pci_resource_len(pdev, 0);
    udev->num_cells = min_t(u32, udev->bar0_size / CELL_STRIDE, MAX_CELLS);

    dev_info(&pdev->dev, "UniCell accelerator: BAR0=%lld bytes, %u cells\n",
             (long long)udev->bar0_size, udev->num_cells);

    /* Register char device */
    ret = alloc_chrdev_region(&unicell_devt, 0, 1, DRIVER_NAME);
    if (ret)
        return ret;

    cdev_init(&udev->cdev, &unicell_fops);
    udev->cdev.owner = THIS_MODULE;
    ret = cdev_add(&udev->cdev, unicell_devt, 1);
    if (ret)
        goto err_chrdev;

    unicell_class = class_create(DRIVER_NAME);
    if (IS_ERR(unicell_class)) {
        ret = PTR_ERR(unicell_class);
        goto err_cdev;
    }

    udev->device = device_create(unicell_class, &pdev->dev,
                                 unicell_devt, udev, "unicell0");
    if (IS_ERR(udev->device)) {
        ret = PTR_ERR(udev->device);
        goto err_class;
    }

    pci_set_drvdata(pdev, udev);
    g_udev = udev;

    dev_info(&pdev->dev, "/dev/unicell0 ready — %u UniCells available\n",
             udev->num_cells);
    return 0;

err_class:
    class_destroy(unicell_class);
err_cdev:
    cdev_del(&udev->cdev);
err_chrdev:
    unregister_chrdev_region(unicell_devt, 1);
    return ret;
}

static void unicell_remove(struct pci_dev *pdev)
{
    struct unicell_dev *udev = pci_get_drvdata(pdev);
    device_destroy(unicell_class, unicell_devt);
    class_destroy(unicell_class);
    cdev_del(&udev->cdev);
    unregister_chrdev_region(unicell_devt, 1);
    g_udev = NULL;
    dev_info(&pdev->dev, "UniCell driver removed\n");
}

static const struct pci_device_id unicell_pci_ids[] = {
    { PCI_DEVICE(UNICELL_VENDOR, UNICELL_DEVICE) },
    { 0, }
};
MODULE_DEVICE_TABLE(pci, unicell_pci_ids);

static struct pci_driver unicell_driver = {
    .name     = DRIVER_NAME,
    .id_table = unicell_pci_ids,
    .probe    = unicell_probe,
    .remove   = unicell_remove,
};

module_pci_driver(unicell_driver);

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Imago-UniCell Project");
MODULE_DESCRIPTION("PCIe driver for Imago-UniCell FPGA accelerator (YPCB-00338-1P1)");
MODULE_VERSION("0.1");
