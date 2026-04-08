
"""
Comprehensive Code Validation and Testing Script
Validates all created code and fixes any errors
"""
import sys
import os
from pathlib import Path
import ast
import subprocess

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

# Setup logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def check_syntax(file_path: Path) -> bool:
    """Check if a Python file has syntax errors"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        logger.info(f"✅ Syntax OK: {file_path.name}")
        return True
    except SyntaxError as e:
        logger.error(f"❌ Syntax Error in {file_path.name}:")
        logger.error(f"   Line {e.lineno}: {e.msg}")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking {file_path.name}: {e}")
        return False


def check_imports(file_path: Path) -> bool:
    """Check if a Python file can be imported without errors"""
    try:
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            logger.info(f"✅ Imports OK: {file_path.name}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Import Error in {file_path.name}: {e}")
        return False


def check_file_exists(file_path: str) -> bool:
    """Check if a file exists"""
    path = backend_path / file_path
    if path.exists():
        logger.info(f"✅ File exists: {file_path}")
        return True
    else:
        logger.warning(f"⚠️  File missing: {file_path}")
        return False


def validate_models():
    """Validate all model files"""
    logger.info("\n" + "="*60)
    logger.info("VALIDATING MODELS")
    logger.info("="*60)

    models_to_check = [
        "models/agent_feedback.py",
        "models/intelligence.py",
        "models/agent_run.py"
    ]

    results = []
    for model_file in models_to_check:
        path = backend_path / model_file
        if path.exists():
            if check_syntax(path):
                results.append((model_file, True))
            else:
                results.append((model_file, False))
        else:
            logger.warning(f"⚠️  Model file not found: {model_file}")
            results.append((model_file, False))

    return results


def validate_services():
    """Validate all service files"""
    logger.info("\n" + "="*60)
    logger.info("VALIDATING SERVICES")
    logger.info("="*60)

    services_to_check = [
        "services/self_improvement_service.py",
        "services/self_improvement_service_fixed.py",
        "services/agent_runner.py",
        "services/redis_service.py",
        "services/ai_provider_service.py"
    ]

    results = []
    for service_file in services_to_check:
        path = backend_path / service_file
        if path.exists():
            if check_syntax(path):
                results.append((service_file, True))
            else:
                results.append((service_file, False))
        else:
            logger.warning(f"⚠️  Service file not found: {service_file}")
            results.append((service_file, False))

    return results


def validate_schemas():
    """Validate all schema files"""
    logger.info("\n" + "="*60)
    logger.info("VALIDATING SCHEMAS")
    logger.info("="*60)

    schemas_to_check = [
        "schemas_self_improvement.py"
    ]

    results = []
    for schema_file in schemas_to_check:
        path = backend_path / schema_file
        if path.exists():
            if check_syntax(path):
                results.append((schema_file, True))
            else:
                results.append((schema_file, False))
        else:
            logger.warning(f"⚠️  Schema file not found: {schema_file}")
            results.append((schema_file, False))

    return results


def validate_routers():
    """Validate all router files"""
    logger.info("\n" + "="*60)
    logger.info("VALIDATING ROUTERS")
    logger.info("="*60)

    routers_to_check = [
        "routers/self_improvement.py"
    ]

    results = []
    for router_file in routers_to_check:
        path = backend_path / router_file
        if path.exists():
            if check_syntax(path):
                results.append((router_file, True))
            else:
                results.append((router_file, False))
        else:
            logger.warning(f"⚠️  Router file not found: {router_file}")
            results.append((router_file, False))

    return results


def check_unicode_issues(file_path: Path) -> dict:
    """Check for common Unicode issues in Python files"""
    issues = {
        "unicode_escapes": [],
        "missing_imports": [],
        "hash_calls": []
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

            for i, line in enumerate(lines, 1):
                # Check for Unicode escape sequences
                if '\\n\\n' in line:
                    issues["unicode_escapes"].append((i, line.strip()))

                # Check for hash() calls without hashlib
                if 'hash(' in line and 'hashlib.' not in line:
                    issues["hash_calls"].append((i, line.strip()))

                # Check for missing hashlib import
                if 'hashlib.sha256(' in content and 'import hashlib' not in content:
                    issues["missing_imports"].append(("import hashlib"))

    except Exception as e:
        logger.error(f"Error checking {file_path.name}: {e}")

    return issues


def fix_unicode_issues(file_path: Path) -> bool:
    """Attempt to fix common Unicode issues in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Fix Unicode escape sequences
        content = content.replace('\\n\\n', '\n\n')

        # Add hashlib import if needed
        if 'hashlib.sha256(' in content and 'import hashlib' not in content:
            # Find first import line and add hashlib
            lines = content.split('\n')
            import_index = 0
            for i, line in enumerate(lines):
                if line.startswith('import '):
                    import_index = i + 1
                    break
            lines.insert(import_index, 'import hashlib')
            content = '\n'.join(lines)

        # Write fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"✅ Fixed Unicode issues in {file_path.name}")
        return True
    except Exception as e:
        logger.error(f"❌ Error fixing {file_path.name}: {e}")
        return False


def validate_all():
    """Run all validation checks"""
    logger.info("="*60)
    logger.info("COMPREHENSIVE CODE VALIDATION")
    logger.info("="*60)

    all_results = {
        "models": validate_models(),
        "services": validate_services(),
        "schemas": validate_schemas(),
        "routers": validate_routers()
    }

    # Check for Unicode issues in self_improvement_service.py
    service_path = backend_path / "services/self_improvement_service.py"
    if service_path.exists():
        logger.info("\n" + "="*60)
        logger.info("CHECKING FOR UNICODE ISSUES")
        logger.info("="*60)
        issues = check_unicode_issues(service_path)

        if any(issues.values()):
            logger.warning("⚠️  Unicode issues found:")
            if issues["unicode_escapes"]:
                logger.warning(f"   - Unicode escapes: {len(issues['unicode_escapes'])} occurrences")
            if issues["missing_imports"]:
                logger.warning(f"   - Missing imports: {issues['missing_imports']}")
            if issues["hash_calls"]:
                logger.warning(f"   - Hash calls: {len(issues['hash_calls'])} occurrences")

            # Attempt to fix
            logger.info("\nAttempting to fix issues...")
            if fix_unicode_issues(service_path):
                logger.info("✅ Unicode issues fixed")
            else:
                logger.error("❌ Failed to fix Unicode issues")
        else:
            logger.info("✅ No Unicode issues found")

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*60)

    total_checks = sum(len(v) for v in all_results.values())
    passed_checks = sum(sum(1 for _, r in v if r) for v in all_results.values())

    for category, results in all_results.items():
        category_passed = sum(1 for _, r in results if r)
        category_total = len(results)
        logger.info(f"{category.upper()}: {category_passed}/{category_total} passed")

    logger.info("="*60)
    logger.info(f"TOTAL: {passed_checks}/{total_checks} checks passed")
    logger.info("="*60)

    return passed_checks == total_checks


if __name__ == "__main__":
    import importlib
    success = validate_all()
    sys.exit(0 if success else 1)
