# Smart Research Assistant - Web Frontend

A modern Python web interface for the Smart Research Assistant, built with Streamlit and powered by FastRMCP for reliable AI research operations.

## Features

### 🔬 **Core Research Capabilities**
- **Multi-step Research Workflow**: Web search → Content analysis → Fact checking → Report generation → Storage
- **Real-time Progress Tracking**: Live updates on each research step with detailed status
- **Interactive Results Display**: Formatted reports with comprehensive metadata
- **Research History**: Track and revisit previous research sessions

### 🛡️ **RMCP Reliability Features**
- **Automatic Retry**: Exponential backoff for failed operations
- **Idempotency**: Prevents duplicate processing with unique keys
- **ACK/NACK Tracking**: Confirms successful operation completion
- **Error Recovery**: Graceful handling of API failures and timeouts
- **Reliability Metrics**: Real-time statistics on operation success rates

### 🎯 **User Experience**
- **Modern UI**: Clean, responsive interface with real-time updates
- **Progress Visualization**: Step-by-step progress bars and status indicators
- **RMCP Insights**: Detailed reliability metrics and operation tracking
- **Session Management**: Multi-research support with persistent history
- **Easy Launch**: One-command startup with automatic browser opening

## Quick Start

### 1. **Installation**
```bash
# From rmcp-python directory
uv sync
```

### 2. **Launch Frontend**
```bash
# Option 1: Quick launcher (recommended)
uv run python examples/run_frontend.py

# Option 2: Direct Streamlit
uv run streamlit run examples/research_frontend.py
```

### 3. **Access Interface**
- **URL**: http://localhost:8501
- **Browser**: Automatically opens in 3 seconds

## Usage Guide

### Starting Research

1. **Enter Query**: Type your research question in the main input field
   ```
   Example: "AI impact on software development productivity 2024"
   ```

2. **Advanced Options** (Optional):
   - Custom Research ID for tracking
   - View research workflow details

3. **Click "🚀 Start Research"** to begin the process

### Monitoring Progress

The interface provides real-time updates:

- **📊 Progress Overview**: Current status, completion percentage, RMCP reliability
- **📝 Detailed Log**: Step-by-step progress messages with timestamps
- **🛡️ RMCP Tracking**: Live reliability metrics and operation status

### Research Steps

1. **🔧 Initialization**: Setup FastRMCP tools and configuration
2. **🔍 Web Search**: Find 6 relevant sources on the topic
3. **📊 Content Analysis**: Analyze top 3 sources for insights
4. **✅ Fact Checking**: Verify 2 key claims against sources
5. **📄 Report Generation**: Create comprehensive research report
6. **💾 Save Results**: Store results for future reference

### Viewing Results

Upon completion:

- **📋 Research Report**: Formatted markdown report with findings
- **🛡️ RMCP Metrics**: Reliability statistics and operation details
- **📁 File Storage**: Persistent JSON storage for later access
- **📚 History**: Added to sidebar research history

## Architecture

### Frontend Components

```
research_frontend.py     # Main Streamlit application
├── Header & Branding   # App title and RMCP feature highlights
├── Research Form       # Query input and advanced options
├── Progress Section    # Real-time step tracking and RMCP stats
├── Results Display     # Report visualization and metrics
└── Sidebar Controls    # Settings, history, and navigation
```

### Backend Integration

```
research_backend.py              # Streamlit-compatible wrapper
├── ProgressTracker            # Thread-safe progress management
├── StreamlitResearchAssistant # Async research coordination
└── Integration Layer          # FastRMCP + SmartResearchAssistant
```

### RMCP Integration

The frontend showcases FastRMCP's reliability features:

- **Automatic Retry**: Failed operations retry with exponential backoff
- **Idempotency**: Each research step uses unique keys to prevent duplication
- **ACK/NACK**: Visual confirmation of successful operation completion
- **Progress Tracking**: Real-time visibility into RMCP operation status
- **Error Handling**: Graceful recovery from transient failures

## Configuration

### Environment Setup

The frontend automatically configures FastRMCP for optimal AI workloads:

```python
config = RMCPConfig(
    default_timeout_ms=30000,        # 30s for AI API calls
    max_concurrent_requests=5,       # Rate limiting
    enable_request_logging=True,     # Debug visibility
    deduplication_window_ms=600000   # 10min research dedup
)
```

### Customization Options

**Port Configuration**:
```bash
uv run streamlit run research_frontend.py --server.port 8080
```

**Network Access**:
```bash
uv run streamlit run research_frontend.py --server.address 0.0.0.0
```

## Files Overview

| File | Purpose |
|------|---------|
| `research_frontend.py` | Main Streamlit web application |
| `research_backend.py` | Thread-safe backend wrapper for async research |
| `run_frontend.py` | Quick launcher with dependency checking |
| `smart_research_assistant.py` | Core research logic (FastRMCP + AI tools) |

## Troubleshooting

### Common Issues

**Dependencies Missing**:
```bash
uv sync  # Reinstall all dependencies
```

**Port Already in Use**:
```bash
uv run streamlit run research_frontend.py --server.port 8502
```

**Import Errors**:
```bash
# Ensure you're in the rmcp-python directory
cd rmcp-python
uv run python examples/run_frontend.py
```

**Browser Not Opening**:
- Manually navigate to http://localhost:8501
- Check firewall settings

### Debug Mode

For detailed logging:
```bash
uv run streamlit run research_frontend.py --logger.level debug
```

## Development

### Extending the Frontend

**Add New Research Steps**:
1. Update `ProgressTracker.total_steps` in `research_backend.py`
2. Add step handling in `_conduct_research_with_tracking()`
3. Update step display names in `research_frontend.py`

**Custom UI Components**:
- Modify `display_*_section()` functions in `research_frontend.py`
- Add new Streamlit components and styling

**RMCP Configuration**:
- Adjust `RMCPConfig` parameters in `research_backend.py`
- Add custom retry policies for specific operations

## Related Documentation

- [Smart Research Assistant CLI](smart_research_assistant.py) - Command-line version
- [FastRMCP Documentation](../docs/en/README.md) - Core RMCP features
- [AI Agents Guide](../docs/en/ai-agents.md) - Building reliable AI agents

---

**Built with**: Streamlit + FastRMCP + Python  
**License**: Apache 2.0  
**Status**: Production ready ✅