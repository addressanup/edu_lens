#!/usr/bin/env python3
"""Setup script for Claude Agents Orchestration System."""

from pathlib import Path
from setuptools import setup, find_packages

# Read the README file
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

# Core dependencies (subset of requirements.txt for basic installation)
install_requires = [
    "anthropic>=0.28.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "sqlalchemy>=2.0.23",
    "alembic>=1.12.1",
    "psycopg2-binary>=2.9.9",
    "redis>=5.0.1",
    "pyyaml>=6.0.1",
    "python-dotenv>=1.0.0",
    "click>=8.1.7",
    "rich>=13.7.0",
    "requests>=2.31.0",
    "httpx>=0.25.0",
    "aiohttp>=3.9.0",
    "tqdm>=4.66.0",
    "loguru>=0.7.2",
    "aiofiles>=23.2.1",
    "orjson>=3.9.10",
    "cryptography>=41.0.7",
    "python-dateutil>=2.8.2",
    "uuid6>=2023.5.2",
    "tenacity>=8.2.3",
]

# Development dependencies
dev_requires = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "black>=23.11.0",
    "isort>=5.12.0",
    "flake8>=6.1.0",
    "mypy>=1.7.0",
    "types-requests>=2.31.0",
    "types-redis>=4.6.0",
    "types-pyyaml>=6.0.12",
]

# Documentation dependencies
docs_requires = [
    "mkdocs>=1.5.3",
    "mkdocs-material>=9.5.0",
]

setup(
    name="claude-agents-orchestration",
    version="1.0.0-alpha",
    author="Your Organization",
    author_email="dev@your-org.com",
    description="Multi-agent AI orchestration platform for end-to-end software project delivery",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/claude-agents-orchestration",
    project_urls={
        "Bug Tracker": "https://github.com/your-org/claude-agents-orchestration/issues",
        "Documentation": "https://github.com/your-org/claude-agents-orchestration/wiki",
        "Source Code": "https://github.com/your-org/claude-agents-orchestration",
    },
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Typing :: Typed",
    ],
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={
        "skills": ["*.md"],
        "templates": ["*.md", "*.yaml"],
        "database": ["*.sql"],
    },
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=install_requires,
    extras_require={
        "dev": dev_requires,
        "docs": docs_requires,
        "all": dev_requires + docs_requires,
    },
    entry_points={
        "console_scripts": [
            "cao=cli:main",
            "claude-orchestrator=cli:main",
            "orchestrate=cli:main",
        ],
    },
    keywords=[
        "ai",
        "agents",
        "orchestration",
        "claude",
        "automation",
        "code-generation",
        "software-development",
        "multi-agent",
    ],
    zip_safe=False,
)
