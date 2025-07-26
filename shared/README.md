# VirtualPyTest Shared Library

Common utilities, models, and configuration shared across all VirtualPyTest services.

## 📦 **What's Included**

- **Configuration**: Environment settings, database config, security settings
- **Data Models**: Common data structures used across services
- **Utilities**: Helper functions, validators, constants
- **Device Configs**: Hardware and device configuration files

## 🔧 **Installation**

```bash
# Install as editable package
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

## 📁 **Structure**

```
shared/lib/
├── config/
│   ├── settings.py          # Shared configuration classes
│   ├── environments.py      # Environment-specific configs
│   └── devices/             # Device configuration files
├── models/
│   ├── device.py           # Device data models
│   └── device_types.py     # Device type definitions
├── utils/
│   ├── validators.py       # Validation utilities
│   ├── constants.py        # System constants
│   └── exceptions.py       # Custom exceptions
└── __init__.py
```

## 🔧 **Environment Variables**

Copy the environment template and configure your credentials:

```bash
# Copy template
cp env.example .env

# Edit with your values
nano .env
```

Required environment variables (see `env.example`):
- `CLOUDFLARE_R2_ENDPOINT` - Cloudflare R2 endpoint URL
- `CLOUDFLARE_R2_ACCESS_KEY_ID` - Access key ID
- `CLOUDFLARE_R2_SECRET_ACCESS_KEY` - Secret access key  
- `CLOUDFLARE_R2_PUBLIC_URL` - Public URL for file access
- `NEXT_PUBLIC_SUPABASE_URL` - Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Supabase anonymous key

## 🚀 **Usage**

### Configuration
```python
from shared.lib.config.settings import shared_config

# Access configuration
db_config = shared_config.database
security_config = shared_config.security
```

### Data Models
```python
from shared.lib.models.device import Device
from shared.lib.models.device_types import DeviceType

# Create device instance
device = Device(
    id="device1",
    name="Test Device",
    type=DeviceType.ANDROID_MOBILE
)
```

### Utilities
```python
from shared.lib.utils.validators import validate_email
from shared.lib.utils.constants import DEFAULT_TIMEOUT

# Use validation
is_valid = validate_email("user@example.com")

# Use constants
timeout = DEFAULT_TIMEOUT
```

## 🔧 **Configuration Management**

### Environment Variables
The shared library reads from these environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=virtualpytest

# Security
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Device Configuration
Device configurations are stored in `lib/config/devices/`:

```python
# Load device configuration
from shared.lib.config.devices import load_device_config

appium_config = load_device_config('appium_remote.json')
```

## 🧪 **Testing**

```bash
# Run tests (if available)
python -m pytest tests/

# Type checking
mypy shared/lib/
```

## 📝 **Adding New Shared Components**

1. **Models**: Add to `lib/models/`
2. **Configuration**: Add to `lib/config/`
3. **Utilities**: Add to `lib/utils/`
4. **Update `__init__.py`**: Export new components

## 🔄 **Versioning**

The shared library follows semantic versioning. When making changes:

1. **Patch** (1.0.1): Bug fixes, documentation
2. **Minor** (1.1.0): New features, backward compatible
3. **Major** (2.0.0): Breaking changes

## 🤝 **Contributing**

1. Add new components following existing patterns
2. Update documentation
3. Ensure backward compatibility
4. Test across all services that use shared lib

## 📋 **Dependencies**

Minimal dependencies to keep shared library lightweight:

- `typing-extensions`: Type hints
- `pydantic`: Data validation
- `python-dotenv`: Environment variables
- `requests`: HTTP client
- `structlog`: Logging
- `orjson`: Fast JSON handling 