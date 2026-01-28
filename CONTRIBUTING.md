
# Contributing to AD-HDTV

Thank you for your interest in contributing!

## Branching
- Use `main` for stable releases.
- Use `dev` for ongoing development.
- Feature branches: `feature/<short-description>`

## Commit Messages
- Use short, imperative messages (e.g., "add Roku client stub").

## No Binaries or Build Folders
- Do not commit build outputs, binaries, or IDE folders.
- See .gitignore for details.

## Where to Place New Features
- Backend/server code: `server/` (or `AD_HDTV/` if not split yet)
- Android client: `clients/android/`
- Roku client: `clients/roku/`
- Docs: `docs/`

---

For questions, open an issue or discussion.

## 🚀 Quick Start

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/yourusername/webgridplayer.git
   cd webgridplayer
   ```
3. **Create** a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
4. **Create** a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
5. **Make** your changes and test thoroughly
6. **Submit** a pull request

## 🎯 Ways to Contribute

### 🐛 Bug Reports
- Use the [GitHub Issues](https://github.com/yourusername/webgridplayer/issues) page
- Check if the issue already exists
- Provide detailed reproduction steps
- Include system information (OS, Python version, VLC version)
- Add screenshots or videos if relevant

### 💡 Feature Requests
- Use [GitHub Discussions](https://github.com/yourusername/webgridplayer/discussions) for ideas
- Describe the use case and benefits
- Consider implementation complexity
- Be open to alternative approaches

### 🔧 Code Contributions
- Fix bugs or implement new features
- Improve documentation
- Add test coverage
- Optimize performance
- Enhance user experience

### 📖 Documentation
- Improve README clarity
- Add usage examples
- Create tutorials or guides
- Fix typos and grammar
- Translate to other languages

## 🏗️ Development Setup

### Prerequisites
- Python 3.8+
- VLC Media Player
- Git

### Development Dependencies
```bash
pip install -r requirements.txt
# Additional dev dependencies
pip install pytest black flake8 mypy
```

### Code Structure
```
webgridplayer/
├── webgridplayer.py      # Main application
├── requirements.txt      # Dependencies
├── install_webgridplayer.sh  # Installation script
├── run_webgridplayer.sh     # Run script
├── test_stream_extraction.py  # Tests
└── examples.py          # Usage examples
```

### Key Classes
- `VideoStreamExtractor`: Web scraping and stream detection
- `VideoPlayer`: Individual VLC player wrapper
- `WebGridPlayer`: Main application and GUI

## 🧪 Testing

### Running Tests
```bash
# Test stream extraction
python test_stream_extraction.py

# Test installation
python test_installation.py

# Manual testing
python webgridplayer.py
```

### Test Coverage
When adding new features, please include tests for:
- Web extraction patterns
- GUI functionality (where possible)
- Error handling
- Cross-platform compatibility

## 📝 Coding Standards

### Python Style
- Follow **PEP 8** style guidelines
- Use **Black** for code formatting: `black webgridplayer.py`
- Use **flake8** for linting: `flake8 webgridplayer.py`
- Add **type hints** where appropriate

### Code Quality
- Write clear, self-documenting code
- Add docstrings for classes and methods
- Handle exceptions gracefully
- Use meaningful variable and function names

### Git Commit Messages
Use the conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Examples:
- `feat: add fullscreen mode support`
- `fix: resolve VLC initialization error on Windows`
- `docs: improve installation instructions`
- `test: add stream extraction unit tests`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## 🎨 UI/UX Guidelines

### Design Principles
- **Simplicity**: Keep the interface clean and intuitive
- **Consistency**: Follow established UI patterns
- **Accessibility**: Consider users with disabilities
- **Performance**: Ensure responsive interactions

### PyQt Guidelines
- Use appropriate layouts (QVBoxLayout, QHBoxLayout, QGridLayout)
- Provide keyboard shortcuts for common actions
- Show progress for long-running operations
- Display helpful error messages

## 🌐 Web Extraction Guidelines

### Adding New Site Support
When adding support for new websites:

1. **Analyze** the site's video delivery method
2. **Test** extraction thoroughly
3. **Handle** edge cases and errors
4. **Document** the extraction method
5. **Respect** robots.txt and rate limits

### Extraction Patterns
```python
def extract_custom_site(self, url: str, soup: BeautifulSoup) -> List[Dict]:
    """Extract streams from a custom site."""
    streams = []
    
    # Your extraction logic here
    # Look for video elements, JSON data, etc.
    
    return streams
```

### Best Practices
- Use appropriate user agents
- Implement rate limiting
- Handle different video qualities
- Support both live and VOD content
- Provide meaningful stream titles

## 🔒 Security Considerations

### Web Scraping
- Never execute arbitrary JavaScript
- Validate and sanitize all URLs
- Use timeouts for network requests
- Handle SSL/TLS certificates properly

### Local Files
- Validate file paths and extensions
- Check file permissions
- Handle large files gracefully

## 🌍 Internationalization

### Adding Translations
We welcome translations to make WebGridPlayer accessible worldwide:

1. Create translation files in `translations/` directory
2. Use Qt's internationalization system
3. Test with different languages and locales
4. Update documentation for new languages

## 📋 Pull Request Process

### Before Submitting
- [ ] Test your changes thoroughly
- [ ] Update documentation if needed
- [ ] Add or update tests
- [ ] Follow coding standards
- [ ] Write clear commit messages

### PR Template
When submitting a pull request, please include:

- **Description**: What does this PR do?
- **Motivation**: Why is this change needed?
- **Testing**: How was this tested?
- **Screenshots**: For UI changes
- **Breaking Changes**: Any compatibility issues?

### Review Process
1. **Automated checks** must pass (if implemented)
2. **Code review** by maintainers
3. **Testing** on different platforms
4. **Documentation** review
5. **Merge** when approved

## 🎖️ Recognition

Contributors will be recognized in:
- README.md acknowledgments section
- CHANGELOG.md for significant contributions
- GitHub contributor stats
- Special mentions for major features

## 📞 Getting Help

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Email**: maintainer@webgridplayer.org (if available)

### Development Questions
- Check existing issues and discussions first
- Provide context and specific questions
- Include relevant code snippets
- Be patient and respectful

## 📄 License

By contributing to WebGridPlayer, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

Thank you for contributing to WebGridPlayer! Your efforts help make this tool better for everyone. 🙏