# Configuration Guide

## Authentication

Two options:

- Interactive (dev): `use_interactive_auth: true` — opens a browser to sign in
- Service principal (CI/CD): `use_interactive_auth: false` — set `client_id`, `tenant_id`, and provide `client_secret` via environment variable

Required permission for service principals: `Item.ReadWrite.All`.

## Finding Your Configuration Values

### Workspace ID

1. Go to [Microsoft Fabric](https://app.fabric.microsoft.com)
2. Navigate to your workspace
3. The workspace ID is in the URL: `https://app.fabric.microsoft.com/groups/{workspace-id}/...`

### Tenant ID

1. Go to [Microsoft Fabric](https://app.fabric.microsoft.com)
2. Navigate to your workspace
3. Click your profile photo (top right).
4. See Tenant details

```

## Environment Variables

Environment variables take precedence over `config.json` settings. This is the recommended approach for managing secrets and for CI/CD environments.

### Supported Environment Variables

| Environment Variable | Config Equivalent | Description |
|---------------------|-------------------|-------------|
| `FABRIC_CLIENT_SECRET` | `fabric.client_secret` | Service principal client secret for authentication |
| `AZURE_TENANT_ID` | `fabric.tenant_id` | Azure AD / Entra ID tenant ID |
| `AZURE_CLIENT_ID` | `fabric.client_id` | Azure AD application (service principal) client ID |
| `AZURE_CLIENT_SECRET` | `fabric.client_secret` | Alternative to `FABRIC_CLIENT_SECRET` (Azure SDK standard) |

### Azure SDK Environment Variables

The tool uses Azure Identity SDK's `DefaultAzureCredential`, which automatically checks these environment variables for authentication:

| Environment Variable | Description |
|---------------------|-------------|
| `AZURE_TENANT_ID` | Azure AD tenant ID for service principal auth |
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Service principal client secret |
| `AZURE_CLIENT_CERTIFICATE_PATH` | Path to PFX/PEM certificate (alternative to secret) |
| `AZURE_USERNAME` | Username for username/password auth (not recommended) |
| `AZURE_PASSWORD` | Password for username/password auth (not recommended) |

### Precedence Order

Configuration values are resolved in this order (first found wins):

1. **Environment variables** (highest priority)
2. **Config file** (`config.json`)
3. **Default values** (lowest priority)

### Setting Environment Variables

```powershell
# Windows (PowerShell) - Session only
$env:FABRIC_CLIENT_SECRET = "<your-secret>"
$env:AZURE_TENANT_ID = "<your-tenant-id>"

# Windows (PowerShell) - Persistent for user
[Environment]::SetEnvironmentVariable("FABRIC_CLIENT_SECRET", "<your-secret>", "User")

# Linux/Mac (bash) - Session only
export FABRIC_CLIENT_SECRET="<your-secret>"
export AZURE_TENANT_ID="<your-tenant-id>"

# Linux/Mac (bash) - Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export FABRIC_CLIENT_SECRET="<your-secret>"' >> ~/.bashrc
```

### Azure Key Vault Integration (Production)

For production deployments, we recommend storing secrets in Azure Key Vault and retrieving them at runtime. Example approach:

```powershell
# Retrieve secret from Key Vault and set as environment variable
$env:FABRIC_CLIENT_SECRET = az keyvault secret show `
    --vault-name "my-keyvault" `
    --name "fabric-client-secret" `
    --query "value" -o tsv

# Then run the converter
python src/main.py rdf-upload ontology.ttl
```

Or use managed identity with Key Vault references in your CI/CD pipeline.

## Security Best Practices

- **Never commit secrets** to source control
- **Prefer Managed Identity** for production deployments on Azure
- **Use Azure Key Vault** for storing and managing secrets
- **Use environment variables** for local development secrets
- Keep `src/config.json` in `.gitignore` (already configured)
- **Rotate secrets regularly** and use short-lived credentials when possible

## Config - Interactive authentication

Create `src/config.json`:

```json
{
  "fabric": {
    "workspace_id": "YOUR_WORKSPACE_ID",
    "tenant_id": "YOUR_TENANT_ID",
    "use_interactive_auth": true
  },
  "ontology": { "default_namespace": "usertypes", "id_prefix": 1000000000000 },
  "logging": {
    "level": "INFO",
    "file": "logs/app.log",
    "format": "text",
    "rotation": { "enabled": true, "max_mb": 10, "backup_count": 5 }
  }
}
```

## Config - Service Principal

Note: This has not been tested

```json
{
  "fabric": {
    "workspace_id": "<workspace-id>",
    "tenant_id": "<tenant-id>",
    "client_id": "<app-id>",
    "use_interactive_auth": false,
    "rate_limit": { "enabled": true, "requests_per_minute": 10, "burst": 15 },
    "circuit_breaker": { "enabled": true, "failure_threshold": 5, "recovery_timeout": 60.0, "success_threshold": 2 }
  }
}
```


## Configuration Options

### Fabric Settings

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `workspace_id` | string | Yes | Your Microsoft Fabric workspace GUID |
| `ontology_id` | string | No | Specific ontology ID (leave empty for name-based operations) |
| `api_base_url` | string | Yes | Fabric API base URL (default shown above) |
| `tenant_id` | string | Yes | Azure AD tenant ID |
| `client_id` | string | Yes | Azure AD application client ID |
| `client_secret` | string | No | Client secret (use env var; avoid storing in files) |
| `use_interactive_auth` | boolean | Yes | Use interactive browser login (true) or service principal (false) |

### Ontology Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `default_namespace` | string | "usertypes" | Default namespace for custom types |
| `id_prefix` | integer | 1000000000000 | Starting ID for generated entity/property IDs |

### Logging Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `level` | string | "INFO" | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `file` \| `log_file` | string | `logs/app.log` | Path to log file (if omitted, logs stream to console only) |
| `format` | string | `text` | Set to `json` (or `structured: true`) to enable structured logging |
| `rotation.enabled` | boolean | true | Toggle rotating file handler when a file path is configured |
| `rotation.max_mb` | integer | 10 | Maximum size (in MB) of each log file before rotation |
| `rotation.backup_count` | integer | 5 | Number of rotated log files to retain |

Example structured log entry:

```json
{
  "timestamp": "2026-01-01T12:00:00.123Z",
  "level": "INFO",
  "logger": "fabric_client",
  "message": "Ontology upload complete",
  "workspace_id": "<guid>"
}
```

### Rate Limiting Settings

Used to avoid 429s by throttling proactively. Defaults are conservative. See official [Fabric throttling](https://learn.microsoft.com/en-us/rest/api/fabric/articles/throttling).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `rate_limit.enabled` | boolean | true | Enable client-side rate limiting |
| `rate_limit.requests_per_minute` | integer | 10 | Long-term request rate |
| `rate_limit.burst` | integer | 15 | Short burst capacity |

Tuning: lower the rate if you hit 429s; raise modestly if you never do.

### Fabric API Limits Settings

Validates ontology definitions against Fabric API limits before upload. These limits help prevent API errors and ensure compatibility.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `limits.max_entity_name_length` | integer | 256 | Max characters in entity type name |
| `limits.max_property_name_length` | integer | 256 | Max characters in property name |
| `limits.max_relationship_name_length` | integer | 256 | Max characters in relationship name |
| `limits.max_definition_size_kb` | integer | 1024 | Max total definition size (KB) |
| `limits.warn_definition_size_kb` | integer | 768 | Warning threshold for definition size |
| `limits.max_entity_types` | integer | 500 | Max entity types per ontology |
| `limits.max_relationship_types` | integer | 500 | Max relationship types per ontology |
| `limits.max_properties_per_entity` | integer | 200 | Max properties per entity type |
| `limits.max_entity_id_parts` | integer | 5 | Max properties in entityIdParts |

**Example Configuration:**

```json
{
  "fabric": {
    "limits": {
      "max_entity_name_length": 256,
      "max_definition_size_kb": 1024,
      "max_entity_types": 500
    }
  }
}
```

**Programmatic Usage:**

```python
from src.core.validators import FabricLimitsValidator

validator = FabricLimitsValidator(
    max_entity_name_length=256,
    max_definition_size_kb=1024,
)

errors = validator.validate_all(entity_types, relationship_types)
if validator.has_errors(errors):
    for e in validator.get_errors_only(errors):
        print(f"ERROR: {e.message}")
```

### EntityIdParts Configuration

Controls how `entityIdParts` (unique entity identifiers) are inferred for entity types. This is important for Fabric to correctly identify and deduplicate entities.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `entity_id_parts.strategy` | string | `"auto"` | Inference strategy (see below) |
| `entity_id_parts.custom_patterns` | array | `[]` | Additional patterns to recognize as primary keys |
| `entity_id_parts.explicit_mappings` | object | `{}` | Entity name to property names mapping |

**Strategies:**

| Strategy | Behavior |
|----------|----------|
| `auto` | Match property names against primary key patterns, then first valid type |
| `first_valid` | Use first String/BigInt property |
| `explicit` | Only use explicit mappings |
| `none` | Never auto-set entityIdParts |

**Example Configuration:**

```json
{
  "ontology": {
    "entity_id_parts": {
      "strategy": "auto",
      "custom_patterns": ["asset_code", "record_id"],
      "explicit_mappings": {
        "Machine": ["serialNumber"],
        "Product": ["productCode", "batchId"]
      }
    }
  }
}
```

**Default Primary Key Patterns (recognized by auto strategy):**
- `id`, `identifier`, `pk`, `primary_key`, `primarykey`, `key`
- `uuid`, `guid`, `oid`, `object_id`, `objectid`
- `entity_id`, `entityid`, `record_id`, `recordid`
- `unique_id`, `uniqueid`

**Programmatic Usage:**

```python
from src.core.validators import EntityIdPartsInferrer

# Auto inference with custom patterns
inferrer = EntityIdPartsInferrer(
    strategy="auto",
    custom_patterns=["asset_code"],
    explicit_mappings={"Machine": ["serialNumber"]}
)

# Apply to all entities
updated_count = inferrer.infer_all(entity_types)
```

### Circuit Breaker Settings

Prevents cascading failures when the API is unhealthy.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `circuit_breaker.enabled` | boolean | true | Enable circuit breaker |
| `circuit_breaker.failure_threshold` | integer | 5 | Failures before opening circuit |
| `circuit_breaker.recovery_timeout` | float | 60.0 | Wait before attempting recovery |
| `circuit_breaker.success_threshold` | integer | 2 | Successes to fully close circuit |

### Local Validation Rate Limiting (Security)

The `ValidationRateLimiter` protects against resource exhaustion when exposing validation as a service. Configure these when building validation endpoints or services.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `requests_per_minute` | integer | 30 | Max validation requests per minute |
| `max_content_size_mb` | float | 50 | Max content size in MB per validation |
| `max_concurrent` | integer | 5 | Max concurrent validation operations |
| `max_memory_percent` | float | 80 | Reject when system memory exceeds this % |
| `enabled` | boolean | true | Enable/disable rate limiting |

**Programmatic Usage:**

```python
from src.core.validators import ValidationRateLimiter

# Configure rate limiter
limiter = ValidationRateLimiter(
    requests_per_minute=30,
    max_content_size_mb=50,
    max_concurrent=5,
    max_memory_percent=80,
)

# Check before validation
allowed, reason = limiter.check_validation_allowed(content)
if not allowed:
    return {"error": reason}, 429

# Perform validation
result = validate(content)
```

### URL Security (SSRF Protection)

The `URLValidator` provides SSRF (Server-Side Request Forgery) protection for any URL handling.

**Default Allowed Protocols:** `https` only
**Default Allowed Ports:** `443`, `8443`
**Blocked:** Private IPs (10.x.x.x, 192.168.x.x, 127.0.0.1, etc.), localhost

**Trusted Ontology Domains (default):**
- `w3.org`, `purl.org`, `schema.org`, `xmlns.com`
- `github.com`, `raw.githubusercontent.com`

**Programmatic Usage:**

```python
from src.core.validators import URLValidator

# Basic validation
url = URLValidator.validate_url("https://example.com/ontology.ttl")

# Ontology-specific validation (trusted domains)
url = URLValidator.validate_ontology_url("https://www.w3.org/2002/07/owl#")

# Custom domain allowlist
url = URLValidator.validate_url(
    "https://internal.company.com/ontology.ttl",
    allowed_domains=['company.com']
)
```

## Troubleshooting

### "Unauthorized" Error
- Verify tenant_id, client_id, and client_secret
- Check app registration permissions
- Ensure you have Contributor access to the workspace

### "Invalid workspace_id"
- Confirm the workspace ID is correct
- Verify workspace has Ontology feature enabled
- Check you have access to the workspace

### Interactive auth not working
- Ensure you're using the correct tenant_id
- Try signing out and back in
- Check browser allows popups from Microsoft login

## Configuration Validation

Quick sanity check:

```powershell
python src/main.py test
```

## Multiple Configurations

You can maintain multiple configurations:

```powershell
# Development
python src\main.py rdf-upload sample.ttl --config config.dev.json

# Production
python src\main.py rdf-upload sample.ttl --config config.prod.json
```

