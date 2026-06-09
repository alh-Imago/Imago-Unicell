# General

General purpose formats — BCD decimal and Q8.24 fixed-point arithmetic.

## Formats

- `BCD_Decimal`
- `FixedPoint_Q8_24`

## Usage

```python
from cell_format import FormatRegistry
reg = FormatRegistry.get_default()
fmt = reg.get("BCD_Decimal")
print(fmt.to_dict())
```

## Author

Imago UniCell Project

## License

MIT
