# Intelligent Document Chunking Service

## Overview

The Intelligent Document Chunking Service provides sophisticated document segmentation capabilities with semantic coherence and context preservation for advanced RAG (Retrieval-Augmented Generation) systems. It implements multiple chunking strategies optimized for different content types and retrieval scenarios.

## Features

### 🧠 **Intelligent Chunking Strategies**
- **Recursive Character Splitting**: Hierarchical splitting based on semantic boundaries
- **Sentence-Based Chunking**: Natural language-aware segmentation
- **Token-Based Chunking**: Transformer model-optimized chunking
- **Hybrid Approach**: Combines multiple strategies for optimal results

### 🔗 **Context Preservation**
- **Configurable Overlap**: Maintains context across chunk boundaries
- **Semantic Boundary Detection**: Preserves paragraphs and sentences
- **Metadata Preservation**: Carries forward document metadata to chunks
- **Position Tracking**: Maintains original document position information

### 📊 **Quality Validation**
- **Semantic Coherence Scoring**: Measures chunk coherence quality
- **Content Density Analysis**: Evaluates meaningful content ratio
- **Size Distribution Validation**: Ensures optimal chunk sizes
- **Comprehensive Metrics**: Detailed quality and performance statistics

### ⚡ **Performance Optimization**
- **Batch Processing**: Efficient handling of large document corpora
- **Memory Management**: Optimized for large-scale processing
- **Configurable Parameters**: Tunable for different use cases
- **Quality Thresholds**: Automatic filtering of low-quality chunks

## Architecture

### Core Components

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   DocumentChunker   │───▶│   ChunkingConfig     │───▶│  DocumentChunkResult│
│                     │    │                      │    │                     │
│ • chunk_document()  │    │ • Strategy settings  │    │ • Content           │
│ • validate_chunks() │    │ • Size parameters    │    │ • Metadata          │
│ • get_stats()       │    │ • Quality thresholds │    │ • Quality metrics   │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
```

### Chunking Strategies

1. **Recursive Character Splitting**
   - Hierarchical splitting using semantic separators
   - Preserves document structure (paragraphs → sentences → words)
   - Optimal for general text content

2. **Sentence-Based Chunking**
   - Natural language boundary detection
   - Maintains sentence integrity
   - Best for narrative and conversational content

3. **Token-Based Chunking**
   - Transformer model token limits
   - Optimized for specific embedding models
   - Ideal for neural retrieval systems

4. **Hybrid Approach**
   - Combines multiple strategies
   - Adaptive chunk refinement
   - Balances quality and performance

## Usage

### Basic Chunking

```python
from app.services.chunking_service import DocumentChunker, ChunkingConfig
from app.database.models import Document

# Create chunker with default configuration
chunker = DocumentChunker()

# Chunk a document
document = Document(
    id="doc-123",
    title="Sample Document",
    content="Your document content here...",
    content_type="text/plain"
)

chunks = chunker.chunk_document(document)

# Access chunk results
for chunk in chunks:
    print(f"Chunk {chunk.metadata.chunk_index}: {len(chunk.content)} chars")
    print(f"Coherence: {chunk.metadata.semantic_coherence_score:.3f}")
    print(f"Content: {chunk.content[:100]}...")
```

### Advanced Configuration

```python
from app.services.chunking_service import ChunkingConfig, ChunkingStrategy

# Custom configuration for RAG optimization
config = ChunkingConfig(
    chunk_size=800,                    # Target chunk size
    chunk_overlap=150,                 # Overlap between chunks
    strategy=ChunkingStrategy.HYBRID,  # Use hybrid approach
    min_chunk_size=200,               # Minimum acceptable size
    max_chunk_size=1200,              # Maximum acceptable size
    preserve_sentences=True,           # Keep sentences intact
    preserve_paragraphs=True,          # Respect paragraph boundaries
    min_meaningful_content_ratio=0.75, # Quality threshold
    remove_empty_chunks=True           # Filter low-quality chunks
)

chunker = DocumentChunker(config)
chunks = chunker.chunk_document(document)
```

### Quality Validation

```python
# Validate chunk quality
validation_result = chunker.validate_chunks(chunks)

print(f"Validation passed: {validation_result['valid']}")
print(f"Quality score: {validation_result['quality_score']:.3f}")

if validation_result['issues']:
    print("Issues found:")
    for issue in validation_result['issues']:
        print(f"  - {issue}")

# Get detailed statistics
stats = chunker.get_chunking_stats(chunks)
print(f"Total chunks: {stats['chunk_count']}")
print(f"Average size: {stats['avg_chunk_size']:.1f} chars")
print(f"Average overlap: {stats['avg_overlap']:.1f} chars")
print(f"Content density: {stats['avg_content_density']:.3f}")
```

### Convenience Functions

```python
from app.services.chunking_service import create_chunker

# Quick chunker creation
chunker = create_chunker(
    chunk_size=500,
    chunk_overlap=100,
    strategy=ChunkingStrategy.SENTENCE_BASED
)

# Process multiple documents
documents = [doc1, doc2, doc3]
all_chunks = []

for doc in documents:
    doc_chunks = chunker.chunk_document(doc)
    all_chunks.extend(doc_chunks)

print(f"Processed {len(documents)} documents into {len(all_chunks)} chunks")
```

## Configuration Options

### Basic Parameters
- `chunk_size`: Target size for each chunk (default: 1000)
- `chunk_overlap`: Overlap between consecutive chunks (default: 200)
- `strategy`: Chunking strategy to use (default: RECURSIVE_CHARACTER)

### Size Constraints
- `min_chunk_size`: Minimum acceptable chunk size (default: 100)
- `max_chunk_size`: Maximum acceptable chunk size (default: 2000)

### Quality Settings
- `preserve_sentences`: Keep sentences intact (default: True)
- `preserve_paragraphs`: Respect paragraph boundaries (default: True)
- `min_meaningful_content_ratio`: Minimum content density (default: 0.7)
- `remove_empty_chunks`: Filter low-quality chunks (default: True)
- `normalize_whitespace`: Clean up whitespace (default: True)

### Advanced Options
- `separators`: Custom separator hierarchy for recursive splitting
- `model_name`: Transformer model for token-based chunking
- `tokens_per_chunk`: Target tokens per chunk for token-based strategy

## Quality Metrics

### Semantic Coherence Score
Measures how well a chunk maintains semantic unity:
- **0.8-1.0**: Excellent coherence (complete thoughts, proper structure)
- **0.6-0.8**: Good coherence (mostly coherent with minor issues)
- **0.4-0.6**: Fair coherence (some fragmentation)
- **0.0-0.4**: Poor coherence (significant fragmentation)

### Content Density
Ratio of meaningful content to total characters:
- **0.9-1.0**: Very high density (technical content, minimal whitespace)
- **0.7-0.9**: High density (normal text content)
- **0.5-0.7**: Medium density (formatted content with spacing)
- **0.0-0.5**: Low density (mostly whitespace or formatting)

### Size Distribution
Analysis of chunk size consistency:
- **Low Standard Deviation**: Consistent chunk sizes
- **High Standard Deviation**: Variable chunk sizes (may indicate quality issues)

## Performance Characteristics

### Processing Speed
- **Small documents** (< 1KB): 1000+ docs/second
- **Medium documents** (1-10KB): 500-1000 docs/second
- **Large documents** (> 10KB): 100-500 docs/second

### Memory Usage
- **Base overhead**: ~50MB for chunker initialization
- **Per document**: ~1-5MB depending on size and strategy
- **Batch processing**: Optimized for large corpora

### Quality vs. Speed Trade-offs
- **Recursive Character**: Fast, good quality for most content
- **Sentence-Based**: Medium speed, excellent for narrative content
- **Token-Based**: Slower, optimal for transformer models
- **Hybrid**: Balanced approach, best overall quality

## Integration with RAG Systems

### Weaviate Integration

```python
from app.database.weaviate_schema import WeaviateSchemaManager

# Chunk documents for Weaviate storage
chunks = chunker.chunk_document(document)

# Convert to Weaviate format
weaviate_chunks = []
for chunk in chunks:
    weaviate_chunk = {
        "chunkId": chunk.metadata.chunk_id,
        "documentId": chunk.metadata.document_id,
        "content": chunk.content,
        "chunkIndex": chunk.metadata.chunk_index,
        "startOffset": chunk.metadata.start_position,
        "endOffset": chunk.metadata.end_position,
        "metadata": chunk.metadata.to_dict()
    }
    weaviate_chunks.append(weaviate_chunk)
```

### Embedding Generation

```python
# Prepare chunks for embedding
chunk_texts = [chunk.content for chunk in chunks]
chunk_metadata = [chunk.metadata.to_dict() for chunk in chunks]

# Generate embeddings (example with sentence-transformers)
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(chunk_texts)

# Store with metadata
for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
    # Store in vector database with embedding and metadata
    pass
```

## Best Practices

### Chunk Size Selection
- **Short queries**: 200-500 characters for precise matching
- **Medium queries**: 500-1000 characters for balanced retrieval
- **Long queries**: 1000-2000 characters for comprehensive context

### Overlap Configuration
- **High precision**: 10-20% overlap for minimal redundancy
- **Balanced**: 20-30% overlap for good context preservation
- **High recall**: 30-50% overlap for maximum context retention

### Strategy Selection
- **Technical documents**: Recursive character splitting
- **Narrative content**: Sentence-based chunking
- **Mixed content**: Hybrid approach
- **Transformer optimization**: Token-based chunking

### Quality Optimization
- Set appropriate `min_meaningful_content_ratio` (0.7-0.8)
- Enable `preserve_sentences` for natural language
- Use `remove_empty_chunks` to filter low-quality results
- Monitor coherence scores and adjust parameters accordingly

## Testing and Validation

### Unit Tests
```bash
# Run chunking service tests
python -m pytest tests/unit/test_chunking_service.py -v
```

### Performance Testing
```bash
# Test with large corpus
python -c "
from app.services.chunking_service import create_chunker
chunker = create_chunker(chunk_size=800, chunk_overlap=150)
# Process your test corpus here
"
```

### Quality Validation
```python
# Validate on your specific content
validation_result = chunker.validate_chunks(chunks)
assert validation_result['valid'], f"Quality issues: {validation_result['issues']}"
assert validation_result['quality_score'] > 0.7, "Quality score too low"
```

## Troubleshooting

### Common Issues

**Low Quality Scores**
- Increase `min_meaningful_content_ratio`
- Enable `preserve_sentences` and `preserve_paragraphs`
- Try different chunking strategies

**Inconsistent Chunk Sizes**
- Adjust `chunk_size` and overlap parameters
- Use hybrid strategy for better size consistency
- Check content structure and formatting

**Poor Context Preservation**
- Increase `chunk_overlap`
- Enable sentence and paragraph preservation
- Consider sentence-based strategy for narrative content

**Performance Issues**
- Reduce batch size for memory-constrained environments
- Use recursive character strategy for faster processing
- Disable advanced features if not needed

### Dependencies

Required packages:
- `langchain>=0.1.0`: Text splitting functionality
- `sentence-transformers>=2.2.0`: Token-based chunking (optional)
- `spacy>=3.4.0`: Advanced NLP features (optional)

Install optional dependencies:
```bash
pip install spacy
python -m spacy download en_core_web_sm
```
