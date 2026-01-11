# Epic 5B: World Rule RAG Content Generation

## Epic Summary

**Epic 5B** extends the character-specific RAG content generation system (Epic 5) by integrating world rules into the generation process. When generating sub-chapter content, the system retrieves semantically relevant world rules and includes them in the LLM prompt to ensure consistency with established universe mechanics and constraints.

---

## User Story

**As an author**, I want world rules to be automatically included in content generation prompts, so that the AI-generated content naturally respects my established universe constraints without me having to manually reference every rule.

---

## Acceptance Criteria

### Core Functionality
- [ ] System retrieves relevant world rules during content generation
- [ ] Rules filtered by book applicability (via `world_rule_books` junction table)
- [ ] Rules ranked by semantic similarity to generation prompt
- [ ] Top N most relevant rules included in LLM prompt (configurable, default: 5-10)
- [ ] Rules presented to LLM with clear context (title, description, category)
- [ ] System gracefully handles cases where no relevant rules found

### Integration with Character RAG
- [ ] World rule RAG runs in parallel with character context retrieval
- [ ] Combined prompt includes both character voice context and world rules
- [ ] Rule retrieval does not significantly increase generation latency (<500ms overhead)
- [ ] Character-specific rules can be prioritized for that character's chapters

### Performance & Reliability
- [ ] Rule retrieval cached when possible (Redis)
- [ ] Fallback to empty rules list if ChromaDB unavailable
- [ ] Generation succeeds even if rule retrieval fails
- [ ] Async embedding ensures rules available for immediate use

### User Control
- [ ] Author can preview which rules will be used before generating
- [ ] Author can manually add/remove rules from generation context
- [ ] System respects rule accuracy ratings (low-accuracy rules weighted down)
- [ ] Author can disable world rule RAG per sub-chapter if desired

---

## Technical Architecture

### Service: WorldRuleRAGProvider

```python
class WorldRuleRAGProvider:
    """
    Retrieves and formats world rules for inclusion in content generation prompts.
    Integrates with Character RAG to provide comprehensive generation context.
    """
    
    def __init__(self):
        self.chromadb = ChromaDBClient()
        self.cache = RedisCache()
        self.db = SupabaseClient()
    
    async def get_rules_for_generation(
        self,
        prompt: str,
        plot_points: str,
        book_id: str,
        trilogy_id: str,
        max_rules: int = 10,
        similarity_threshold: float = 0.65
    ) -> List[WorldRuleContext]:
        """
        Retrieve relevant world rules for content generation.
        
        Args:
            prompt: User's writing prompt
            plot_points: Key plot points for the sub-chapter
            book_id: Current book being written
            trilogy_id: Trilogy identifier
            max_rules: Maximum number of rules to return
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of world rules with similarity scores, sorted by relevance
        """
        # 1. Combine prompt and plot points for comprehensive search
        search_text = f"{prompt}\n\n{plot_points}"
        
        # 2. Check cache first
        cache_key = f"rules:{book_id}:{hash(search_text)}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # 3. Semantic search in ChromaDB
        results = await self.chromadb.query(
            collection=f"{trilogy_id}_world_rules",
            query_text=search_text,
            n_results=max_rules * 2  # Get extra for filtering
        )
        
        # 4. Filter to rules applicable to this book
        rule_ids = [r['id'] for r in results 
                   if r['similarity'] >= similarity_threshold]
        
        rules = await self._get_rules_for_book_filtered(
            book_id, 
            rule_ids,
            max_rules
        )
        
        # 5. Enhance with similarity scores and accuracy
        enhanced_rules = []
        for rule in rules:
            similarity = next(
                r['similarity'] for r in results 
                if r['id'] == rule.id
            )
            
            # Weight down low-accuracy rules
            if rule.accuracy_rate < 0.5:
                similarity *= 0.7
            
            enhanced_rules.append(
                WorldRuleContext(
                    rule=rule,
                    similarity=similarity,
                    relevance_reason=self._explain_relevance(rule, search_text)
                )
            )
        
        # 6. Sort by adjusted similarity
        enhanced_rules.sort(key=lambda x: x.similarity, reverse=True)
        enhanced_rules = enhanced_rules[:max_rules]
        
        # 7. Cache results (15 minutes)
        await self.cache.set(cache_key, enhanced_rules, ttl=900)
        
        return enhanced_rules
    
    async def _get_rules_for_book_filtered(
        self, 
        book_id: str, 
        rule_ids: List[str],
        max_rules: int
    ) -> List[WorldRule]:
        """Get rules that apply to this book, from the provided rule IDs."""
        query = """
            SELECT DISTINCT wr.*, wre.status as embedding_status
            FROM world_rules wr
            JOIN world_rule_books wrb ON wr.id = wrb.world_rule_id
            LEFT JOIN world_rule_embeddings wre ON wr.id = wre.world_rule_id
            WHERE wrb.book_id = $1
              AND wr.id = ANY($2)
              AND (wre.status = 'completed' OR wre.status IS NULL)
            ORDER BY wr.accuracy_rate DESC
            LIMIT $3
        """
        return await self.db.fetch(query, book_id, rule_ids, max_rules)
    
    def format_rules_for_prompt(
        self, 
        rules: List[WorldRuleContext]
    ) -> str:
        """
        Format rules for inclusion in LLM generation prompt.
        
        Returns formatted string ready to insert into prompt.
        """
        if not rules:
            return ""
        
        formatted = "WORLD RULES TO RESPECT:\n\n"
        
        for i, rule_ctx in enumerate(rules, 1):
            rule = rule_ctx.rule
            formatted += f"{i}. [{rule.category}] {rule.title}\n"
            formatted += f"   {rule.description}\n"
            
            # Add relevance note for high-similarity rules
            if rule_ctx.similarity > 0.85:
                formatted += f"   ⚠️ Highly relevant to this scene\n"
            
            formatted += "\n"
        
        formatted += "NOTE: These rules should guide but not constrain creative storytelling. "
        formatted += "Intentional rule breaks are acceptable when they serve the narrative.\n"
        
        return formatted
    
    def _explain_relevance(self, rule: WorldRule, search_text: str) -> str:
        """Generate human-readable explanation of why rule is relevant."""
        # Simple keyword matching for explanation
        # In production, could use LLM to generate explanation
        keywords = rule.title.lower().split() + rule.category.lower().split()
        matched = [kw for kw in keywords if kw in search_text.lower()]
        
        if matched:
            return f"Matched keywords: {', '.join(matched[:3])}"
        return "Semantic similarity to scene context"
```

---

## Integration with Content Generation Pipeline

### Enhanced Generation Flow

```python
class EnhancedNovelGenerationPipeline:
    """
    Combines character RAG with world rule RAG for comprehensive context.
    """
    
    def __init__(self):
        self.character_rag = CharacterRAGGenerator()
        self.world_rule_rag = WorldRuleRAGProvider()
        self.llm_client = LLMClient()
    
    async def generate_sub_chapter(
        self,
        request: GenerationRequest
    ) -> SubChapterContent:
        """
        Generate sub-chapter content with both character and world rule context.
        """
        # 1. Retrieve character context (existing Epic 5 functionality)
        character_context = await self.character_rag.get_character_context(
            character_id=request.character_perspective,
            book_id=request.book_id
        )
        
        # 2. Retrieve world rule context (NEW: Epic 5B)
        world_rule_context = await self.world_rule_rag.get_rules_for_generation(
            prompt=request.writing_prompt,
            plot_points=request.plot_points,
            book_id=request.book_id,
            trilogy_id=request.trilogy_id
        )
        
        # 3. Build comprehensive prompt
        full_prompt = self._build_generation_prompt(
            request=request,
            character_context=character_context,
            world_rules=world_rule_context
        )
        
        # 4. Generate content with LLM
        content = await self.llm_client.generate(
            prompt=full_prompt,
            model="mistral-7b-local",
            max_tokens=request.target_word_count * 2
        )
        
        # 5. Store generation metadata (which rules were used)
        await self._store_generation_metadata(
            sub_chapter_id=request.sub_chapter_id,
            used_rules=[r.rule.id for r in world_rule_context]
        )
        
        return content
    
    def _build_generation_prompt(
        self,
        request: GenerationRequest,
        character_context: CharacterContext,
        world_rules: List[WorldRuleContext]
    ) -> str:
        """
        Construct comprehensive LLM prompt with all context.
        """
        prompt_parts = []
        
        # Character voice and context
        prompt_parts.append("CHARACTER CONTEXT:")
        prompt_parts.append(character_context.format_for_prompt())
        prompt_parts.append("\n")
        
        # World rules
        if world_rules:
            prompt_parts.append(
                self.world_rule_rag.format_rules_for_prompt(world_rules)
            )
            prompt_parts.append("\n")
        
        # Writing prompt and plot points
        prompt_parts.append("WRITING TASK:")
        prompt_parts.append(f"Prompt: {request.writing_prompt}")
        prompt_parts.append(f"Plot Points: {request.plot_points}")
        prompt_parts.append(f"Target Length: ~{request.target_word_count} words")
        
        if request.tone:
            prompt_parts.append(f"Tone: {request.tone}")
        
        if request.additional_instructions:
            prompt_parts.append(f"\nAdditional Instructions: {request.additional_instructions}")
        
        prompt_parts.append("\n")
        prompt_parts.append("Generate the sub-chapter content now:")
        
        return "\n".join(prompt_parts)
```

---

## Data Models

### WorldRuleContext

```python
class WorldRuleContext(BaseModel):
    """
    World rule with generation-specific metadata.
    """
    rule: WorldRule
    similarity: float  # 0.0 to 1.0
    relevance_reason: str
    
    @property
    def is_critical(self) -> bool:
        """Rules with very high similarity are critical to follow."""
        return self.similarity > 0.85
    
    @property
    def weighted_priority(self) -> float:
        """Priority score considering both similarity and rule accuracy."""
        return self.similarity * self.rule.accuracy_rate
```

### SubChapterGenerationMetadata

```python
class SubChapterGenerationMetadata(BaseModel):
    """
    Track which rules were used during generation for analytics.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sub_chapter_id: str
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    
    # World Rules Used
    world_rule_ids: List[str]  # Rules included in generation prompt
    world_rule_similarities: Dict[str, float]  # rule_id -> similarity score
    
    # Character Context Used
    character_id: str
    character_context_chunks: int
    
    # Generation Parameters
    model_used: str
    prompt_token_count: int
    generation_token_count: int
    
    # Quality Indicators
    rules_followed_count: Optional[int] = None  # From consistency check
    rules_violated_count: Optional[int] = None
```

### Database Schema Addition

```sql
-- Track which rules were used during each generation
CREATE TABLE sub_chapter_generation_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sub_chapter_id UUID NOT NULL REFERENCES sub_chapters(id) ON DELETE CASCADE,
    generation_timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Context used
    world_rule_ids UUID[],  -- Array of rule IDs used
    character_id UUID REFERENCES characters(id),
    
    -- Generation details
    model_used VARCHAR,
    prompt_token_count INTEGER,
    generation_token_count INTEGER,
    
    -- Post-generation analysis (populated by consistency checker)
    rules_followed_count INTEGER,
    rules_violated_count INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gen_metadata_subchapter ON sub_chapter_generation_metadata(sub_chapter_id);
CREATE INDEX idx_gen_metadata_timestamp ON sub_chapter_generation_metadata(generation_timestamp);

-- Query to find which rules are most often used
CREATE VIEW world_rule_usage_analytics AS
SELECT 
    wr.id,
    wr.title,
    wr.category,
    COUNT(DISTINCT sgm.sub_chapter_id) as times_used_in_generation,
    AVG(sgm.rules_followed_count::FLOAT / 
        NULLIF(sgm.rules_followed_count + sgm.rules_violated_count, 0)) as avg_adherence_rate
FROM world_rules wr
LEFT JOIN sub_chapter_generation_metadata sgm ON wr.id = ANY(sgm.world_rule_ids)
GROUP BY wr.id, wr.title, wr.category;
```

---

## Expected Functions & Capabilities

### 1. **Semantic Rule Retrieval**
- **Function**: `get_rules_for_generation()`
- **Capability**: Uses ChromaDB to find rules semantically similar to writing prompt and plot points
- **Performance**: <500ms retrieval time
- **Caching**: Redis cache for frequently accessed rule sets

### 2. **Book-Specific Filtering**
- **Function**: `_get_rules_for_book_filtered()`
- **Capability**: Only includes rules applicable to current book via junction table
- **Ensures**: Rules that shouldn't apply yet (e.g., Book 3 rules in Book 1) are excluded

### 3. **Priority Weighting**
- **Function**: `weighted_priority` property
- **Capability**: Rules weighted by:
  - Semantic similarity to scene (0.65-1.0)
  - Historical accuracy rate (down-weight frequently dismissed rules)
  - Critical flag for extremely relevant rules (>0.85 similarity)

### 4. **Prompt Formatting**
- **Function**: `format_rules_for_prompt()`
- **Capability**: Formats rules in clear, structured way for LLM
- **Includes**: Category tags, relevance indicators, gentle guidance notes
- **Tone**: Guiding rather than restrictive

### 5. **Parallel Context Retrieval**
- **Function**: `generate_sub_chapter()` orchestration
- **Capability**: Fetches character context and world rules concurrently
- **Benefit**: No sequential bottleneck, faster generation start

### 6. **Generation Metadata Tracking**
- **Function**: `_store_generation_metadata()`
- **Capability**: Records which rules were included for later analysis
- **Analytics**: Can identify:
  - Which rules are most frequently relevant
  - Which rules correlate with violations
  - Rule usage patterns across trilogy

### 7. **Graceful Degradation**
- **Function**: Error handling in `get_rules_for_generation()`
- **Capability**: Generation continues even if:
  - ChromaDB unavailable
  - No relevant rules found
  - Embedding service down
- **Fallback**: Empty rules list, log warning

### 8. **User Control & Preview**
- **Function**: Preview endpoint (to be implemented in Epic 5B UI)
- **Capability**: Author sees which rules will be used before generating
- **Allows**: Manual override - add/remove specific rules

### 9. **Relevance Explanation**
- **Function**: `_explain_relevance()`
- **Capability**: Shows author why each rule was included
- **Helps**: Author understand system reasoning
- **Future**: Could use LLM for more sophisticated explanations

### 10. **Cross-Reference with Violations**
- **Function**: Integration with `ConsistencyChecker`
- **Capability**: After generation, compare:
  - Which rules were included in prompt
  - Which rules were violated in output
- **Learning**: Identifies if prompt inclusion actually prevents violations

---

## Integration Points

### With Epic 5 (Character RAG)
- World rule RAG runs in parallel with character context retrieval
- Combined into single comprehensive generation prompt
- Character-specific rules can be prioritized for POV chapters

### With Epic 3 (World Rules Engine)
- Uses same ChromaDB collection: `{trilogy_id}_world_rules`
- Respects rule accuracy rates from violation tracking
- Filters by book associations via `world_rule_books` junction table

### With Epic 6 (Sub-Chapter Management)
- Stores generation metadata in `sub_chapter_generation_metadata`
- Links generated content to rules that guided it
- Enables "which rules influenced this chapter?" queries

### With Epic 7 (Consistency Checking)
- Feeds list of used rules to post-generation checker
- Checker prioritizes validating rules that were in generation prompt
- Creates feedback loop: did including rule in prompt prevent violation?

---

## Performance Considerations

### Latency Budget
- **Rule Retrieval**: 200-400ms
- **Character Context**: 100-200ms (existing)
- **Prompt Construction**: <50ms
- **Total Overhead**: ~500ms before LLM generation starts
- **Mitigation**: Parallel retrieval, aggressive caching

### Caching Strategy
```python
# Cache key structure
cache_key = f"rules:{book_id}:{hash(prompt + plot_points)}"

# TTL: 15 minutes (900 seconds)
# Rationale: Prompts often similar during same writing session

# Cache invalidation:
# - On rule update (clear all caches for that trilogy)
# - On book association change
# - Manual "refresh rules" button in UI
```

### ChromaDB Query Optimization
- Request `max_rules * 2` to account for filtering
- Similarity threshold: 0.65 (balance precision vs recall)
- Maximum rules in prompt: 10 (avoid overwhelming LLM)
- Index on `world_rule_books` for fast filtering

---

## Success Metrics

### Effectiveness
- **Violation Reduction**: Rules included in prompt have 50% fewer violations than rules not included
- **Rule Relevance**: Author rates 80%+ of included rules as helpful
- **Generation Quality**: Content rated higher when rules used vs not used

### Performance
- **Retrieval Time**: <500ms for 95th percentile
- **Cache Hit Rate**: >60% during active writing sessions
- **Generation Success**: 99.9% (degradation works)

### Usage
- **Adoption**: 80%+ of generations use world rule RAG
- **Rule Density**: Average 5-8 rules per generation
- **Manual Overrides**: <10% (system picks good defaults)

---

## Future Enhancements

### Advanced Relevance Scoring
- Use LLM to explain why rule is relevant (not just keyword matching)
- Learn from author's manual overrides to improve selection
- A/B test different similarity thresholds per author

### Dynamic Rule Weighting
- Increase weight for rules frequently violated in this book
- Decrease weight for rules with many "intentional break" dismissals
- Character-specific rule weights (some characters break rules more)

### Conflict Detection
- Identify when multiple rules in context contradict each other
- Alert author before generation
- Suggest which rule takes precedence

### Rule Clustering
- Group similar rules together in prompt
- Avoid redundant rules (e.g., 3 rules about same physics constraint)
- Present clustered rules as unified constraint

### Cross-Book Learning
- If author accepts violation in Book 1, suggest updating rule to apply only to Books 2-3
- Track rule evolution across trilogy
- Recommend rule refinements based on actual usage

---

## Implementation Checklist

- [ ] Create `WorldRuleRAGProvider` service class
- [ ] Implement semantic rule retrieval from ChromaDB
- [ ] Build book-specific filtering via junction table queries
- [ ] Create prompt formatting function
- [ ] Integrate with existing `CharacterRAGGenerator`
- [ ] Create `sub_chapter_generation_metadata` table
- [ ] Implement metadata storage on generation
- [ ] Add Redis caching layer
- [ ] Build preview UI in Streamlit
- [ ] Create rule usage analytics view
- [ ] Add error handling and graceful degradation
- [ ] Write integration tests with mock ChromaDB
- [ ] Performance test with 100+ rules
- [ ] Document API endpoints for UI integration

---

## API Endpoints

### Preview Rules for Generation
```
GET /api/world_rules/preview
Query Params:
  - prompt: string (writing prompt)
  - plot_points: string
  - book_id: UUID
  - max_rules: int (optional, default 10)

Response:
{
  "rules": [
    {
      "id": "uuid",
      "title": "string",
      "description": "string",
      "category": "string",
      "similarity": 0.87,
      "relevance_reason": "string",
      "is_critical": true
    }
  ],
  "formatted_prompt_section": "string"
}
```

### Override Rules for Generation
```
POST /api/world_rules/override
Body:
{
  "sub_chapter_id": "uuid",
  "include_rule_ids": ["uuid1", "uuid2"],
  "exclude_rule_ids": ["uuid3"]
}

Response:
{
  "status": "success",
  "rules_used": ["uuid1", "uuid2"]
}
```

### Rule Usage Analytics
```
GET /api/world_rules/analytics/usage
Query Params:
  - trilogy_id: UUID
  - book_id: UUID (optional)

Response:
{
  "most_used_rules": [
    {
      "rule_id": "uuid",
      "title": "string",
      "times_used": 45,
      "avg_adherence_rate": 0.92
    }
  ],
  "least_used_rules": [...],
  "rules_correlating_with_violations": [...]
}
```

---

**Epic Dependencies:**
- Epic 3: World Building & Rules Engine (must be complete)
- Epic 5: Character-Specific RAG Content Generation (must be complete)
- ChromaDB collections for world rules must be populated

**Estimated Effort:** 16-20 hours
**Priority:** High (core generation feature)
**Risk:** Low (builds on proven RAG patterns)

---

*Document Version: 1.0*  
*Created: November 2, 2025*  
*Author: Claude (with Anshula)*
