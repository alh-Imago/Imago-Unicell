# PhysTrix

PhysTrix SI units with CODATA 2018 constants. Dimensional analysis at design time.

## Formats

- `SI_Physics`

## Usage

```python
from cell_format import FormatRegistry
reg = FormatRegistry.get_default()
fmt = reg.get("SI_Physics")
print(fmt.to_dict())
```

## Author

Imago UniCell Project

## License

MIT
