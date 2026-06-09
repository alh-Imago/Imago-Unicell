# MathTrix

MathTrix floating-point stencil computation. Reference implementation of the MIF format pattern.

## Formats

- `MIF`

## Usage

```python
from cell_format import FormatRegistry
reg = FormatRegistry.get_default()
fmt = reg.get("MIF")
print(fmt.to_dict())
```

## Author

Imago UniCell Project

## License

MIT
