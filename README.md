[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![version](https://img.shields.io/badge/version-1.0.0-green)](./)

# MemoryPlus Plugin for ApexGPT/PyGPT (Graphiti Backend)

MemoryPlus is an advanced temporal memory and insight analysis plugin for PyGPT, powered by the Graphiti knowledge graph engine. It enables your AI assistant to develop a deeper, more contextual, and actively analyzed understanding of conversations, user preferences, and evolving topics. By leveraging a graph database, MemoryPlus moves beyond simple vector recall to construct a rich, interconnected web of memories and insights, enhancing the AI's ability to maintain coherent, personalized, and intelligent interactions over extended periods.

This plugin ensures that your AI learns and adapts, transforming raw conversational data into structured knowledge that informs future responses. It offers extensive configurability to tailor its behavior to various use cases, from maintaining consistent chatbot personas to aiding research and productivity.

## Core Functionality

MemoryPlus provides the following key capabilities:

*   **Intelligent Memory Ingestion**: Automatically captures and processes conversational turns, transforming them into structured memory nodes within a knowledge graph.
*   **Active Insight Analysis**: Utilizes a dedicated LLM to analyze ingested memories, extracting entities, relationships, emotions, and topics, enriching the knowledge graph.
*   **Contextual Memory Retrieval**: When generating responses, MemoryPlus intelligently searches its knowledge graph for the most relevant past memories, injecting them into the AI's system prompt for highly contextual replies.
*   **Flexible Database Backends**: Supports both Neo4j and Kuzu graph databases for robust and scalable memory storage.
*   **Configurable Memory Modes**: Offers various pre-defined "Memory Modes" (e.g., Identity, Chatbot, Research) that guide the AI's analytical lens during ingestion and insight generation.
*   **Search Caching**: Implements an LRU cache with TTL and fuzzy matching to optimize memory retrieval performance, reducing redundant calls to the graph engine.
*   **Memory Lifecycle Management**: Provides options for automatic pruning of low-value memories and time-based expiry to keep the knowledge graph lean and relevant.
*   **Sanitization Controls**: Allows for stripping specific elements (tool calls, code blocks) from ingested memories to focus on conversational content.
*   **Asynchronous Processing**: Uses background threads and queues for ingestion and response polling to ensure a smooth user experience without blocking the main application.

## Architecture and Components

MemoryPlus operates through a tightly integrated architecture designed for performance, robustness, and flexibility.

### Graphiti Engine

At its heart, MemoryPlus utilizes the **Graphiti** knowledge graph engine. Graphiti is a separate, specialized component responsible for:

*   **Graph Database Interaction**: Managing connections to and operations within either a Neo4j or Kuzu graph database.
*   **LLM Integration**: Orchestrating calls to large language models for tasks such as:
    *   **Insight Generation**: Analyzing text to extract entities, relationships, emotions, and topics.
    *   **Embedding Generation**: Creating vector embeddings for semantic search using various providers (OpenAI, Ollama, Google).
*   **Memory Operations**: Handling the core logic for ingesting, searching, and deleting memories within the graph.

The Graphiti engine can operate in two primary modes:

*   **Persistent Worker (Default)**: A long-running background process that maintains a live connection to the database and LLM services. This mode is generally more efficient for frequent operations due to reduced startup overhead.
*   **Per-Call Subprocess**: Each Graphiti operation (ingest, search, forget) is executed as a new, short-lived subprocess. This mode is more resource-intensive but can be more resilient to individual operation failures.

### Memory Ingestion

1.  **Event Trigger**: After each `CTX_AFTER` event (i.e., after the AI generates a response), the plugin captures the user input and AI output.
2.  **Queueing**: This conversational turn is packaged as an "episode" and added to an internal **ingestion queue**. This queue prevents the main application from blocking while memories are processed.
3.  **Worker Thread**: A dedicated background thread (`_ingest_loop`) continuously pulls items from the queue.
4.  **Batch Processing**: To optimize database and LLM calls, the worker can process multiple queued items together in batches, with configurable delays.
5.  **Graphiti Processing**: Each batch (or individual item) is sent to the Graphiti engine, which then:
    *   Analyzes the content based on the selected "Memory Mode".
    *   Extracts entities, relationships, and metadata.
    *   Generates vector embeddings for semantic search.
    *   Stores this structured information as interconnected nodes and relationships in the graph database.
6.  **Retries**: Failed ingestion attempts are retried with exponential backoff to enhance reliability.

### Memory Retrieval

1.  **Event Trigger**: Before each `CTX_BEFORE` event (i.e., before the AI generates a response), the plugin initiates a memory search.
2.  **Search Cache Check**: The plugin first checks a local `SearchCache` to see if a similar query has been recently processed. This cache significantly speeds up retrieval for repetitive queries.
3.  **Graphiti Search**: If not cached, the current user input is sent to the Graphiti engine with a specified `search_depth` (context limit).
4.  **Semantic and Contextual Search**: The Graphiti engine performs a sophisticated search across the knowledge graph, leveraging both semantic similarity (via embeddings) and structural relationships (via the graph) to find the most relevant memories.
5.  **Result Formatting**: The retrieved memories are formatted into a concise block.
6.  **System Prompt Injection**: During the `SYSTEM_PROMPT` event, this formatted memory block is injected into the AI's system prompt, providing the AI with crucial context before it generates its response.
7.  **Cache Update**: If the search was not cached, the new results are stored in the `SearchCache`.

### Memory Lifecycle

MemoryPlus includes features to manage the lifespan and relevance of stored memories:

*   **Low-Value Pruning**: Automatically identifies and removes trivial or short conversational snippets that do not contribute significant value to the knowledge graph, based on a configurable word count threshold.
*   **Time-Based Expiry**: Memories older than a specified number of days can be automatically deleted from the database, preventing indefinite growth and ensuring relevance. A daily background check triggers this process.

### Caching

The `SearchCache` is an in-memory, Least Recently Used (LRU) cache with a Time-To-Live (TTL) mechanism. It stores recent memory search results to minimize calls to the Graphiti engine and the underlying database.

*   **Configurable Size and TTL**: Control how many entries the cache holds and how long results remain valid.
*   **Fuzzy Matching**: Allows for a configurable similarity ratio to treat slightly different queries as the same, improving cache hit rates.
*   **Automatic Invalidation**: The cache is automatically cleared when new memories are ingested, ensuring that searches always reflect the most up-to-date knowledge.

## Configuration Options

MemoryPlus offers extensive configuration options, categorized into several tabs within the PyGPT plugin settings, allowing users to fine-tune its behavior.

### General Settings

*   **Auto-Ingest**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: If enabled, conversations are automatically saved to your Graphiti memory after each interaction (user input + AI response). Disabling this requires manual ingestion (e.g., via future commands).
*   **Engine Mode**:
    *   **Type**: Combo (`auto`, `persistent`, `subprocess`)
    *   **Default**: `auto`
    *   **Description**: Determines how the Graphiti engine is executed.
        *   `auto`: Attempts to start a persistent worker. If it fails, falls back to `subprocess` mode.
        *   `persistent`: Starts a long-running Graphiti worker process. Recommended for better performance.
        *   `subprocess`: Executes Graphiti operations in separate, short-lived processes for each call.
*   **Inject Context**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: If enabled, relevant memories retrieved from Graphiti will be injected into the system prompt before the AI generates its response, providing enhanced context.
*   **Context Limit**:
    *   **Type**: Integer (Min: 1, Max: 100)
    *   **Default**: `10`
    *   **Description**: The maximum number of individual relevant memories to retrieve from Graphiti and inject into the AI's context.
*   **Disable Default Vector Store**:
    *   **Type**: Boolean
    *   **Default**: `False`
    *   **Description**: If checked, an explicit instruction will be added to the AI's system prompt, asking it to prioritize Graphiti memories over any other default vector store or context sources it might have.

### Database Settings

*   **Database Backend**:
    *   **Type**: Combo (`Neo4j`, `Kuzu`)
    *   **Default**: `Neo4j`
    *   **Description**: Selects the underlying graph database technology to store your memories.
        *   `Neo4j`: A robust, enterprise-grade graph database. Requires a running Neo4j instance.
        *   `Kuzu`: An embedded, high-performance graph database suitable for local deployments.
*   **Link DB to Preset**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: If enabled, MemoryPlus will create or select a database instance (or a logical partition within a database) named after the currently active PyGPT preset. This isolates memories, allowing different presets to have their own distinct memory banks. If disabled, the `Database Name (Fallback)` will be used.
*   **Neo4j URI**:
    *   **Type**: Text
    *   **Default**: `bolt://localhost:7687`
    *   **Description**: The connection URI for your Neo4j database instance. Only applicable if `Database Backend` is Neo4j.
*   **Neo4j User**:
    *   **Type**: Text
    *   **Default**: `neo4j`
    *   **Description**: The username for authenticating with your Neo4j database. Only applicable if `Database Backend` is Neo4j.
*   **Neo4j Password**:
    *   **Type**: Text (Secret)
    *   **Default**: `password`
    *   **Description**: The password for authenticating with your Neo4j database. This field is masked. Only applicable if `Database Backend` is Neo4j.
*   **Database Name (Fallback)**:
    *   **Type**: Text
    *   **Default**: `neo4j`
    *   **Description**: The default Neo4j database name to use if `Link DB to Preset` is disabled. This also acts as a fallback if a preset name cannot be determined. Only applicable if `Database Backend` is Neo4j.
*   **Kuzu Storage Path**:
    *   **Type**: Text
    *   **Default**: `~/.apex/memories` (or equivalent home directory path)
    *   **Description**: The root directory where Kuzu database files will be stored. Each preset (if `Link DB to Preset` is enabled) will have its own subdirectory here. Only applicable if `Database Backend` is Kuzu.

### Models and Embeddings

*   **Memory Mode**:
    *   **Type**: Combo (`Identity`, `Assistant`, `Chatbot`, `Productivity`, `Research`, `Discourse`, `ResolveEntities`, `MemoryGate`, `CustomPrompt`)
    *   **Default**: `Chatbot`
    *   **Description**: Selects the active memory analysis mode. This determines the conceptual lens through which conversations are analyzed for insights, influencing the type of information extracted and prioritized by Graphiti.
        *   `Identity`: Focuses on personal traits, preferences, and biographical details.
        *   `Assistant`: Emphasizes tasks, instructions, and goal-oriented interactions.
        *   `Chatbot`: General conversational memory, focusing on natural dialogue flow.
        *   `Productivity`: Tracks project details, deadlines, and workflow-related information.
        *   `Research`: Prioritizes facts, data points, and academic or analytical content.
        *   `Discourse`: Analyzes argumentation, viewpoints, and conversational dynamics.
        *   `ResolveEntities`: Explicitly focuses on identifying and disambiguating entities mentioned.
        *   `MemoryGate`: A specialized mode for conditional memory processing (advanced usage).
        *   `CustomPrompt`: Uses the `Custom Analysis Prompt` defined in advanced settings.
*   **Insight Model**:
    *   **Type**: Combo (Uses available models configured in PyGPT)
    *   **Default**: `gpt-4o`
    *   **Description**: The Large Language Model (LLM) used by Graphiti specifically for generating analytical insights (e.g., emotion, topic tagging) from ingested conversational segments. This model performs the "thinking" about your memories.
*   **Graphiti Internal Model**:
    *   **Type**: Combo (Uses available models configured in PyGPT)
    *   **Default**: `gpt-4o`
    *   **Description**: The LLM used by the Graphiti backend for its general internal graph-building operations, entity extraction, and relationship identification. This is Graphiti's primary operational LLM.
*   **Max Context Tokens**:
    *   **Type**: Integer (Min: 1024, Max: 128000)
    *   **Default**: `8192`
    *   **Description**: The maximum token length for the context window of the `Graphiti Internal Model`. Adjust this based on the capabilities of your chosen LLM and the complexity of your memory insights.
*   **Embedding Provider**:
    *   **Type**: Combo (`OpenAI`, `Ollama`, `Google`)
    *   **Default**: `OpenAI`
    *   **Description**: The service provider used for generating vector embeddings. Embeddings are crucial for semantic search, allowing MemoryPlus to find contextually similar memories even if the exact words are not used.
        *   `OpenAI`: Uses OpenAI's embedding models (requires OpenAI API key).
        *   `Ollama`: Uses local Ollama models (requires Ollama to be running locally).
        *   `Google`: Uses Google's embedding models (requires Google API key).
*   **Embedding Model**:
    *   **Type**: Combo (Specific models based on selected provider)
    *   **Default**: `text-embedding-3-small`
    *   **Description**: The specific model used to create vector embeddings for semantic search. Choose a model compatible with your selected `Embedding Provider`.
*   **Override Base URL**:
    *   **Type**: Text
    *   **Default**: (Empty)
    *   **Description**: (Advanced) Allows you to override the default API base URL for the `Graphiti Internal Model`. Useful for self-hosted LLMs or proxy setups.
*   **Override API Key**:
    *   **Type**: Text (Secret)
    *   **Default**: (Empty)
    *   **Description**: (Advanced) Allows you to override the default API key for the `Graphiti Internal Model`. This key will take precedence over any global PyGPT API key for Graphiti's internal LLM.

### Sanitization Rules

These options control how incoming conversational data is cleaned before being stored as memories, allowing you to focus on the most relevant content.

*   **Sanitize Tool Calls**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: If enabled, strips tool usage syntax (e.g., `<tool_code>...</tool_code>`) from memories before ingestion. This focuses memories on conversational content rather than technical execution details.
*   **Sanitize Code Blocks**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: If enabled, strips markdown code blocks (```...```) from memories during ingestion.
*   **Preserve Tagged Code**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: If `Sanitize Code Blocks` is enabled, checking this option will prevent code blocks specifically tagged with `[KEEP_CODE]` from being stripped.
*   **Max Memory Length**:
    *   **Type**: Integer (Min: 100, Max: 10000)
    *   **Default**: `4096`
    *   **Description**: Truncates individual memories to this token length before ingestion. Useful for managing memory footprint and focusing on key parts of longer conversations.

### Intelligence Features

These settings enable and configure intelligent analysis of memories by the Graphiti engine.

*   **Enable Emotion Tagging**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: If enabled, Graphiti will automatically detect and tag memories with relevant emotional contexts (e.g., `[EMOTION: amused]`, `[EMOTION: frustrated]`).
*   **Emotion Sensitivity**:
    *   **Type**: Combo (`Low`, `Medium`, `High`)
    *   **Default**: `Medium`
    *   **Description**: Adjusts how aggressively emotions are detected and tagged by the `Insight Model`. Higher sensitivity may result in more frequent or nuanced emotion tags.
*   **Enable Topic Tagging**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: If enabled, Graphiti will automatically identify and tag memories with relevant topics (e.g., `[TOPIC: linux]`, `[TOPIC: project management]`).
*   **Enable Vibe Scoring**:
    *   **Type**: Boolean
    *   **Default**: `False`
    *   **Description**: If enabled, Graphiti will attempt to assign a numerical "vibe score" (e.g., 0.9 for positive, 0.1 for negative) to memories, representing their overall emotional tone.

### Memory Lifecycle Management

Control how long memories persist and how "low-value" memories are handled.

*   **Auto-Prune Low-Value Memories**:
    *   **Type**: Boolean
    *   **Default**: `False`
    *   **Description**: If enabled, Graphiti will automatically remove memories that are deemed trivial or low-value during ingestion (e.g., simple greetings, one-word acknowledgments).
*   **Low-Value Threshold**:
    *   **Type**: Integer (Min: 1, Max: 50)
    *   **Default**: `3`
    *   **Description**: The minimum number of words a memory must contain to be considered worth retaining if `Auto-Prune Low-Value Memories` is enabled. Memories shorter than this threshold may be discarded.
*   **Enable Manual Memory Flagging**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: Allows you to manually flag memories using specific commands (e.g., `/remember_this`, `/forget_that`) to explicitly control what gets ingested or removed from the graph.
*   **Memory Expiry (Days)**:
    *   **Type**: Integer (Min: 0, Max: 3650)
    *   **Default**: `0`
    *   **Description**: Automatically deletes memories older than this number of days from the knowledge graph. Set to `0` to disable memory expiry (memories will persist indefinitely).

### Advanced Settings

These settings provide fine-grained control over various internal mechanisms and experimental features.

*   **Custom Sanitization Rules**:
    *   **Type**: Text
    *   **Default**: (Empty)
    *   **Description**: A semicolon-separated list of custom regex patterns to apply during memory sanitization. Any text matching these patterns will be removed from memories before ingestion.
*   **Custom Memory Tags**:
    *   **Type**: Text
    *   **Default**: (Empty)
    *   **Description**: A comma-separated list of custom tags that will be applied to all ingested memories. Useful for broad categorization or experimental labeling.
*   **Insight Model Temperature**:
    *   **Type**: Float (Min: 0.0, Max: 1.0, Step: 0.1)
    *   **Default**: `0.3`
    *   **Description**: Adjusts the creativity and randomness of the `Insight Model` when generating analytical insights. Lower values yield more focused, deterministic insights; higher values can produce more varied or speculative insights.
*   **Memory Review Interval (Days)**:
    *   **Type**: Integer (Min: 0, Max: 365)
    *   **Default**: `7`
    *   **Description**: Not yet implemented or fully integrated into the UI. Intended to prompt the user to review memories periodically. Set to `0` to disable.
*   **Enable Memory Feedback**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: Not yet fully integrated into the UI. Intended to allow users to rate memories (e.g., via 👍/👎 emojis) to provide feedback on their relevance or accuracy.
*   **Memory Search Depth**:
    *   **Type**: Integer (Min: 1, Max: 100)
    *   **Default**: `10`
    *   **Description**: (Duplicate of `Context Limit` in General Settings) The number of relevant memories to retrieve during a search operation.
*   **Enable Search Cache**:
    *   **Type**: Boolean
    *   **Default**: `True`
    *   **Description**: If enabled, the plugin will cache recent memory search results to improve performance and reduce calls to the Graphiti engine.
*   **Search Cache Size**:
    *   **Type**: Integer (Min: 0, Max: 100)
    *   **Default**: `8`
    *   **Description**: The maximum number of cached search results to keep in memory. Set to `0` to effectively disable the cache (though `Enable Search Cache` must also be unchecked).
*   **Search Cache TTL (s)**:
    *   **Type**: Integer (Min: 0, Max: 600)
    *   **Default**: `45`
    *   **Description**: The maximum number of seconds a cached search result remains valid before it's considered stale and re-fetched from the Graphiti engine. Set to `0` for immediate expiry (not recommended).
*   **Search Cache Similarity**:
    *   **Type**: Float (Min: 0.0, Max: 1.0, Step: 0.05)
    *   **Default**: `0.85`
    *   **Description**: The similarity ratio (0.0 to 1.0) required between two search queries for them to be considered "the same" by the cache, allowing a cached result to be used for a slightly different but semantically similar query.
*   **Ingestion Queue Size**:
    *   **Type**: Integer (Min: 0, Max: 1000)
    *   **Default**: `50`
    *   **Description**: The maximum number of pending memory ingestion items that can be held in the internal queue. Set to `0` for an unlimited queue size (use with caution).
*   **Ingestion Overflow Policy**:
    *   **Type**: Combo (`drop_new`, `drop_oldest`, `block`)
    *   **Default**: `drop_new`
    *   **Description**: Defines how the ingestion queue behaves when it reaches its maximum size:
        *   `drop_new`: The newest incoming memory item is discarded if the queue is full.
        *   `drop_oldest`: The oldest item in the queue is removed to make space for the new item.
        *   `block`: The main application will pause (block) until space becomes available in the queue.
*   **Ingestion Batch Size**:
    *   **Type**: Integer (Min: 1, Max: 100)
    *   **Default**: `5`
    *   **Description**: The maximum number of memory items that will be processed together in a single batch by the ingestion worker thread. Batching can improve efficiency for database and LLM calls.
*   **Ingestion Batch Delay (ms)**:
    *   **Type**: Integer (Min: 0, Max: 5000)
    *   **Default**: `250`
    *   **Description**: The maximum time (in milliseconds) the ingestion worker will wait to collect additional items to form a batch before processing the current batch. Set to `0` for immediate processing of available items.
*   **Ingestion Retry Attempts**:
    *   **Type**: Integer (Min: 1, Max: 10)
    *   **Default**: `3`
    *   **Description**: The number of times the plugin will attempt to retry a failed memory ingestion operation before giving up.
*   **Ingestion Retry Backoff (ms)**:
    *   **Type**: Integer (Min: 100, Max: 5000)
    *   **Default**: `500`
    *   **Description**: The initial delay (in milliseconds) before retrying a failed ingestion. This delay doubles with each subsequent retry, implementing an exponential backoff strategy.
*   **Runner Timeout (s)**:
    *   **Type**: Integer (Min: 5, Max: 180)
    *   **Default**: `45`
    *   **Description**: The maximum time (in seconds) allowed for a single Graphiti subprocess operation to complete before it's considered timed out. Only applies when `Engine Mode` is `subprocess`.
*   **Custom Analysis Prompt**:
    *   **Type**: Text
    *   **Default**: (Empty)
    *   **Description**: An optional custom prompt that will be used by the `Insight Model` for memory analysis. This prompt is only active when `Memory Mode` is set to `CustomPrompt`.

## Memory Modes

MemoryPlus offers various "Memory Modes" that instruct the Graphiti engine on how to interpret and analyze conversational data. Each mode provides a different analytical lens, helping to extract specific types of insights and build a knowledge graph tailored to a particular use case.

*   **Identity**: Focuses on extracting personal information about the user and the AI, including names, roles, preferences, biographical details, and consistent traits. Ideal for maintaining a strong and consistent persona for the AI.
*   **Assistant**: Concentrates on tasks, goals, instructions, project details, and actionable items. Useful when the AI is primarily functioning as a productivity or task management assistant.
*   **Chatbot**: A general-purpose mode for capturing the flow and content of casual conversations. It aims to build a broad understanding of topics discussed, user interests, and conversational nuances.
*   **Productivity**: Prioritizes information related to work, projects, deadlines, workflows, tools used, and problem-solving steps. Excellent for work-oriented AI applications.
*   **Research**: Emphasizes facts, data points, citations, arguments, scientific concepts, and detailed information. Suited for AI assistants involved in information gathering, synthesis, or academic support.
*   **Discourse**: Analyzes conversational patterns, arguments made, opinions expressed, and the dynamics of interaction. Helps the AI understand viewpoints and argumentative structures.
*   **ResolveEntities**: Specifically aims to identify and disambiguate entities (people, places, organizations, concepts) mentioned in the conversation, ensuring a clear and consistent understanding of who or what is being discussed.
*   **MemoryGate**: An advanced, specialized mode intended for conditional memory processing or specific internal logic within the Graphiti engine. Its behavior is highly dependent on internal Graphiti implementation.
*   **CustomPrompt**: Allows you to define your own unique analysis prompt in the `Custom Analysis Prompt` advanced setting. This gives you complete control over how memories are analyzed.

## Requirements

The MemoryPlus plugin requires the following Python packages, which are listed in `requirements.txt`:

*   `graphiti-core>=0.1.0`
*   `nest_asyncio`
*   `pydantic>=1.10`

These dependencies will be automatically installed when you enable the plugin. Ensure your Python environment is correctly set up to handle these.

## Installation and Usage

(This section typically includes specific steps for installing the plugin into PyGPT and how to enable/use its features. As this information was not explicitly provided in the plugin code, these are placeholders for a complete `README.md`.)

### Installation

1.  Place the `MemoryPlus` plugin directory into your PyGPT plugins folder.
2.  Navigate to the PyGPT settings and enable the MemoryPlus plugin.
3.  Restart PyGPT if prompted.

### Usage

1.  **Configure**: Go to the MemoryPlus plugin settings in PyGPT and adjust the options according to your needs, paying close attention to Database, Models, and Memory Mode settings.
2.  **Engage**: Simply interact with your AI assistant as usual. With `Auto-Ingest` enabled, your conversations will automatically be processed and stored in the knowledge graph.
3.  **Context**: As you converse, MemoryPlus will automatically retrieve and inject relevant memories into the AI's prompt, enhancing the quality and continuity of the dialogue.
4.  **Manual Commands**: (If `Manual Memory Flagging` is enabled) Use specific commands like `/remember_this [text]` or `/forget_that [text]` directly in your chat to explicitly manage memories.

## Troubleshooting

(This section would typically include common issues and their solutions. As this information was not explicitly provided in the plugin code, these are placeholders for a complete `README.md`.)

*   **Graphiti Engine Fails to Start**: Check `Engine Mode` settings. Ensure Neo4j or Ollama services are running if selected. Review plugin logs for error messages.
*   **No Memories Ingested**: Verify `Auto-Ingest` is enabled. Check for any `Ingestion Queue` overflow messages in the logs.
*   **Memory Retrieval Issues**: Confirm `Inject Context` is enabled. Check `Context Limit` and `Search Depth`. Ensure embedding models are correctly configured and accessible.
