# FinTrix

FinTrix financial instruments and currencies. Market constants reconfigurable without recompile.

## Formats

- `Finance_Currency`

## Usage

```python
from cell_format import FormatRegistry
reg = FormatRegistry.get_default()
fmt = reg.get("Finance_Currency")
print(fmt.to_dict())
```

## Author

Imago UniCell Project

## License

MIT
