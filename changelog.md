# Changelog

## [Unreleased] - 2025-02-05

### Added
- Secure environment variables handling for cloud storage access
  - Added support for GCS credentials via .env file
  - Implemented secure credential handling in code execution environment
  - Limited environment variable exposure for enhanced security
  - Fixed SSL compatibility issues with urllib3
- Dataset viewing capability with tabbed interface
- Improved Monaco Editor state preservation when switching between code and dataset tabs
  - Editor state is now maintained when switching between tabs
  - Better performance when switching between code files
  - Smoother transition between code and dataset views
- Enhanced DataFrame UI with DuckDB-inspired design
  - Added sticky headers and improved table styling
  - Added row count display and pagination
  - Improved typography with monospace for numeric values
  - Added alternating row colors for better readability
- Added collapsible Explore section in sidebar for better workspace management
- Added collapsible sidebar with ellipsis toggle
  - Smooth transition animation when collapsing/expanding
  - Maintains state between page reloads
  - Improves workspace real estate management
- Converted Settings page to modal interface
  - Added full-screen dark overlay for better focus
  - Maintained all existing settings functionality
  - Improved accessibility with keyboard navigation

### Fixed
- Issue where Monaco Editor would lose state when switching to dataset tabs
- Improved tab switching performance by reusing editor instance
