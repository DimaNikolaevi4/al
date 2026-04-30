# Changelog

All notable changes to the AI Tutor SPO project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- LoRA adapter support for domain-specific fine-tuning (planned)
- Multi-level summary generation (basic/advanced) (planned)
- Response caching for improved performance (planned)
- Streaming output support for web interface (planned)
- Moodle integration module (planned)
- Audio content generation for accessibility (planned)

### Changed
- Optimize quantization for lower VRAM usage (4-bit/8-bit) (planned)
- Improve conversation memory with summarization (planned)

---

## [0.2.0] - 2024-05-20

### Added
- **Logging System**: Comprehensive logging with multiple levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Type Hints**: Full Python 3.10+ type annotations across all functions and methods
- **Error Handling**: Custom exceptions (`ModelLoadError`, `InferenceError`) with proper error context
- **Configuration**: Environment-based configuration via `.env` file support
- **Chat Interface**: Basic conversational dialogue capability with history support
- **Quiz Generation**: Initial implementation of quiz/question generation (experimental)
- **Unit Tests**: Basic test structure with pytest framework

### Changed
- **Code Quality**: Refactored entire codebase to follow PEP 257 docstring conventions
- **Memory Management**: Added explicit memory cleanup on OOM errors
- **Documentation**: Expanded README with badges, architecture diagram, and detailed setup instructions

### Fixed
- Tokenizer pad token configuration for proper generation
- Input validation for empty lecture texts
- Graceful handling of CUDA out-of-memory errors

### Security
- Added `.env` to `.gitignore` to prevent credential exposure
- Implemented trust_remote_code parameter for model loading

---

## [0.1.1] - 2024-04-28

### Added
- Basic project structure with requirements.txt
- Initial documentation in README.md
- CHECKLIST.md for project tracking

### Changed
- Updated model path to use Mistral Small 3.1 (24B)
- Improved prompt formatting for better summary generation

### Fixed
- Device mapping for multi-GPU systems
- Tokenizer encoding issues with Russian text

---

## [0.1.0] - 2024-04-15

### Added
- **Core Module**: Initial `IntelligentTutor` class implementation
- **Model Loading**: Support for loading Mistral models from Hugging Face Hub
- **Lecture Summarization**: Basic functionality to generate structured lecture summaries
- **PEFT Integration**: Support for loading LoRA adapters via PEFT library
- **GPU Support**: Automatic device mapping with `device_map="auto"`
- **Memory Efficiency**: Float16 precision for reduced memory footprint

### Technical Details
- Base model: `mistralai/Mistral-Small-24B-Instruct-2501`
- Dependencies: PyTorch 2.0+, Transformers 4.35+, PEFT 0.6+
- Initial proof-of-concept demonstrating feasibility of LLM-based tutoring

---

## Version History Summary

| Version | Date | Description |
|---------|------|-------------|
| 0.2.0 | 2024-05-20 | Production-ready code quality, logging, error handling |
| 0.1.1 | 2024-04-28 | Project structure and documentation improvements |
| 0.1.0 | 2024-04-15 | Initial prototype with Mistral integration |

---

[Unreleased]: https://github.com/your-org/ai-tutor-spo/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/your-org/ai-tutor-spo/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/your-org/ai-tutor-spo/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/your-org/ai-tutor-spo/releases/tag/v0.1.0
