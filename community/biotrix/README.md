# BioTrix

BioTrix genomics — DNA, RNA, amino acid sequences. 2-bit base encoding, 16 bases per cell word.

## Formats

- `DNA_4Base`
- `RNA_4Base`
- `Amino20`

## Usage

```python
from cell_format import FormatRegistry
reg = FormatRegistry.get_default()
fmt = reg.get("DNA_4Base")
print(fmt.to_dict())
```

## Author

Imago UniCell Project

## License

MIT
