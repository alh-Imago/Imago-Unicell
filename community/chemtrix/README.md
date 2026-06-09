# ChemTrix

ChemTrix periodic table chemistry. 8-bit element codes, 4 per cell word, property LUTs.

## Formats

- `Chemistry_Element`

## Usage

```python
from cell_format import FormatRegistry
reg = FormatRegistry.get_default()
fmt = reg.get("Chemistry_Element")
print(fmt.to_dict())
```

## Author

Imago UniCell Project

## License

MIT
