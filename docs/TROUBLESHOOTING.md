# Troubleshooting Guide

## Common Issues and Solutions

### Authentication Issues

#### "Unauthorized" or "403 Forbidden"

**Symptoms:** Authentication fails with unauthorized error

**Solutions:**
1. Verify credentials in config.json
2. Check app registration permissions include `Item.ReadWrite.All`
3. Ensure you have Contributor role on the workspace
4. Try interactive auth first: `"use_interactive_auth": true`

```bash
# Test authentication
python main.py test
```

#### Interactive Auth Browser Not Opening

**Solutions:**
1. Check if browser allows popups from Microsoft
2. Try manually copying the authentication URL from terminal
3. Ensure you're on the correct tenant

### Ontology Upload Issues

#### "ItemDisplayNameAlreadyInUse"

**Symptoms:** Upload fails because ontology name exists

**Solutions:**
```bash
# Update existing ontology
python main.py upload sample.ttl --update

# Or use a different name
python main.py upload sample.ttl --name "MyOntology_v2"

# Or delete existing and recreate
python main.py list  # Get ontology ID
python main.py delete <ontology-id>
python main.py upload sample.ttl
```

#### "CorruptedPayload" Error

**Symptoms:** Upload fails with corrupted payload

**Solutions:**
1. Validate TTL syntax: `python main.py convert sample.ttl`
2. Check for special characters in names
3. Ensure parent entities are defined before children
4. Check log file for details: `rdf_import.log`

#### "Invalid baseEntityTypeId"

**Symptoms:** Entity with inheritance fails to upload

**Solutions:**
- Ensure parent class is defined in same ontology
- Check parent entity ID is valid
- Converter automatically orders entities (parents first)

### Parsing Issues

#### "Invalid RDF/TTL syntax"

**Symptoms:** TTL file fails to parse

**Solutions:**
1. Validate TTL syntax online: https://www.w3.org/RDF/Validator/
2. Check for missing prefixes
3. Ensure proper encoding (UTF-8)
4. Look for unclosed brackets or quotes

Example valid TTL:
```turtle
@prefix : <http://example.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:Person a owl:Class ;
    rdfs:label "Person" .
```

#### "No RDF triples found"

**Symptoms:** Parser returns empty result

**Solutions:**
1. Check file is not empty
2. Verify file encoding is UTF-8
3. Ensure prefixes are declared
4. Check namespace declarations

### Configuration Issues

#### "Configuration file not found"

**Solutions:**
```bash
# Create from sample
cp config.sample.json config.json

# Edit with your values
notepad config.json  # Windows
nano config.json     # Linux/Mac
```

#### "Invalid JSON in configuration file"

**Solutions:**
1. Validate JSON syntax: https://jsonlint.com/
2. Check for:
   - Missing commas
   - Extra commas at end of last item
   - Unescaped quotes in strings
   - Missing closing brackets

### Performance Issues

#### Large File Takes Too Long

**Solutions:**
1. Enable progress bars (already included via tqdm)
2. Check file size: `dir sample.ttl` (Windows) or `ls -lh sample.ttl` (Linux/Mac)
3. Split large ontologies into smaller files
4. Increase timeout in config (if needed)

#### Memory Error with Large Files

**Solutions:**
```python
# Process in chunks (if implementing streaming)
# Or increase available memory
# Or split the ontology file
```

### Testing Issues

#### Tests Fail to Run

**Solutions:**
```bash
# Ensure pytest is installed
pip install pytest

# Run with verbose output
python -m pytest tests/ -v

# Check specific failing test
python -m pytest tests/test_converter.py::test_name -v
```

#### Sample Files Not Found

**Solutions:**
```bash
# Ensure you're in project root
cd "C:\Users\ansyeo\OneDrive - Microsoft\01 Azure\Ontology\RDF Import"

# Verify samples exist
ls samples/

# Run from correct directory
python -m pytest tests/test_converter.py -v
```

## Error Messages Reference

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `FileNotFoundError` | Config or TTL file missing | Check file path and ensure file exists |
| `ValueError: Empty TTL content` | Empty or whitespace-only file | Add valid TTL content to file |
| `KeyError: workspace_id` | Missing config field | Add required field to config.json |
| `ConnectionError` | Network issues | Check internet connection |
| `TimeoutError` | API request timeout | Retry or check Fabric service status |

## Logging and Debugging

### Enable Debug Logging

```json
{
  "logging": {
    "level": "DEBUG",
    "log_file": "debug.log"
  }
}
```

Then check the log:
```bash
# Windows
type debug.log | findstr ERROR

# Linux/Mac
grep ERROR debug.log
```

### Verbose Output

```bash
# Run with Python verbose mode
python -v main.py upload sample.ttl

# Or check logs
python main.py upload sample.ttl 2>&1 | tee output.log
```

## Getting Help

### Before Asking for Help

1. ✅ Check this troubleshooting guide
2. ✅ Review error messages in log file
3. ✅ Run `python main.py test` to validate setup
4. ✅ Try with sample files first
5. ✅ Search existing GitHub issues

### Reporting Issues

Include:
- Python version: `python --version`
- Operating system
- Error message (full stack trace)
- Steps to reproduce
- Sample TTL file (if possible)
- Config file (with secrets removed)

```bash
# Collect diagnostic info
python --version
pip list | findstr "rdflib\|pytest\|azure"
python main.py test > diagnostics.txt 2>&1
```

## Quick Diagnostics Checklist

Run through this checklist:

```bash
# 1. Python version
python --version  # Should be 3.9+

# 2. Dependencies installed
pip list

# 3. Config file exists
type config.json  # Windows
cat config.json   # Linux/Mac

# 4. Test connection
python main.py test

# 5. Validate sample TTL
python main.py convert samples/sample_ontology.ttl

# 6. Run tests
python run_tests.py all
```

## Platform-Specific Issues

### Windows

- Use forward slashes in paths: `samples/file.ttl`
- Or double backslashes: `samples\\file.ttl`
- PowerShell may require quotes: `python main.py upload "samples/file.ttl"`

### Linux/Mac

- Check file permissions: `chmod +r sample.ttl`
- Use forward slashes: `samples/file.ttl`
- Virtual env activation: `source .venv/bin/activate`

## Still Having Issues?

1. Check [Configuration Guide](CONFIGURATION.md)
2. Review [API Reference](API_REFERENCE.md)
3. See [Examples](EXAMPLES.md)
4. Open a [GitHub Issue](https://github.com/yourusername/repo/issues)
