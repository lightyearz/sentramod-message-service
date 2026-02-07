# Message Service

**Port:** 8007
**Purpose:** Manage conversations and messages for YouthAI platform

## Overview

The Message Service provides persistent storage for conversations and messages between teens and the AI assistant. It enables conversation history, message retrieval, and integrates with the safety pipeline to store topic classifications and safety metadata.

---

## Features

### ✅ Conversation Management
- Create new conversations for teens
- List conversations with pagination and filtering
- Update conversation titles and status
- Archive, restore, or delete conversations
- Track message counts and last message timestamps

### ✅ Message Persistence
- Store user and assistant messages
- Retrieve message history with pagination
- Store topic tier and safety classifications
- Store safety flags and metadata
- Order messages chronologically

### ✅ Status Tracking
- **Active:** Conversation is active, can add messages
- **Archived:** Conversation is archived, read-only
- **Deleted:** Conversation is soft-deleted, hidden from user

### ✅ Safety Integration
- Store topic tier (Tier 1-4) for each message
- Store topic categories detected
- Store safety flags (PII, toxicity, etc.)
- Query messages by safety tier

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Message Service (8007)          │
└─────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌──────────┐
│ Domain  │  │  App    │  │  Infra   │
│ Entities│  │ Use     │  │ Database │
│         │  │ Cases   │  │ Repos    │
└─────────┘  └─────────┘  └──────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   PostgreSQL     │
                    │ - conversations  │
                    │ - messages       │
                    └──────────────────┘
```

**Clean Architecture:**
- **Domain Layer:** `Conversation`, `Message` entities with business logic
- **Application Layer:** Repository interfaces
- **Infrastructure Layer:** PostgreSQL implementations, database models
- **API Layer:** FastAPI REST endpoints

---

## Database Schema

### conversations table

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    teen_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    status VARCHAR(20) NOT NULL,  -- active, archived, deleted
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    last_message_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',

    INDEX idx_conversations_teen_status (teen_id, status),
    INDEX idx_conversations_teen_last_message (teen_id, last_message_at)
);
```

### messages table

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    topic_tier VARCHAR(20),  -- tier_1, tier_2, tier_3, tier_4
    topic_categories JSONB DEFAULT '[]',
    safety_flags JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    metadata JSONB DEFAULT '{}',

    INDEX idx_messages_conversation_created (conversation_id, created_at),
    INDEX idx_messages_role (role),
    INDEX idx_messages_topic_tier (topic_tier)
);
```

---

## API Endpoints

### Conversation Endpoints

#### POST `/api/v1/conversations`
**Create a new conversation**

Request:
```json
{
  "teen_id": "uuid",
  "title": "Homework Help - Math"
}
```

Response:
```json
{
  "id": "uuid",
  "teen_id": "uuid",
  "title": "Homework Help - Math",
  "status": "active",
  "created_at": "2025-12-01T10:00:00Z",
  "updated_at": "2025-12-01T10:00:00Z",
  "last_message_at": null,
  "message_count": 0,
  "metadata": {}
}
```

#### GET `/api/v1/conversations/{conversation_id}`
**Get a conversation by ID**

Response: Same as create response

#### GET `/api/v1/teens/{teen_id}/conversations`
**Get all conversations for a teen**

Query Parameters:
- `status` (optional): Filter by status (active, archived, deleted)
- `limit` (optional, default 50): Max conversations to return
- `offset` (optional, default 0): Pagination offset

Response:
```json
[
  {
    "id": "uuid",
    "teen_id": "uuid",
    "title": "Homework Help - Math",
    "status": "active",
    "created_at": "2025-12-01T10:00:00Z",
    "updated_at": "2025-12-01T10:15:00Z",
    "last_message_at": "2025-12-01T10:15:00Z",
    "message_count": 5,
    "metadata": {}
  }
]
```

#### PATCH `/api/v1/conversations/{conversation_id}`
**Update a conversation**

Request:
```json
{
  "title": "New Title",
  "status": "archived"  // active, archived, deleted
}
```

Response: Updated conversation object

#### DELETE `/api/v1/conversations/{conversation_id}`
**Delete a conversation (hard delete)**

Response: 204 No Content

---

### Message Endpoints

#### POST `/api/v1/conversations/{conversation_id}/messages`
**Add a message to a conversation**

Request:
```json
{
  "role": "user",  // user, assistant, system
  "content": "Can you help me with my algebra homework?"
}
```

Response:
```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "role": "user",
  "content": "Can you help me with my algebra homework?",
  "topic_tier": null,
  "topic_categories": [],
  "safety_flags": {},
  "created_at": "2025-12-01T10:15:00Z",
  "metadata": {}
}
```

#### GET `/api/v1/conversations/{conversation_id}/messages`
**Get all messages in a conversation**

Query Parameters:
- `limit` (optional, default 100): Max messages to return
- `offset` (optional, default 0): Pagination offset

Response:
```json
[
  {
    "id": "uuid",
    "conversation_id": "uuid",
    "role": "user",
    "content": "Can you help me with my algebra homework?",
    "topic_tier": "tier_1",
    "topic_categories": ["Math", "Homework"],
    "safety_flags": {},
    "created_at": "2025-12-01T10:15:00Z",
    "metadata": {}
  },
  {
    "id": "uuid",
    "conversation_id": "uuid",
    "role": "assistant",
    "content": "Of course! What specific algebra problem are you working on?",
    "topic_tier": null,
    "topic_categories": [],
    "safety_flags": {},
    "created_at": "2025-12-01T10:15:05Z",
    "metadata": {}
  }
]
```

#### GET `/api/v1/conversations/{conversation_id}/with-messages`
**Get conversation with its messages (combined endpoint)**

Query Parameters:
- `limit` (optional, default 100): Max messages to return
- `offset` (optional, default 0): Pagination offset

Response:
```json
{
  "conversation": {
    "id": "uuid",
    "teen_id": "uuid",
    "title": "Homework Help - Math",
    "status": "active",
    "created_at": "2025-12-01T10:00:00Z",
    "updated_at": "2025-12-01T10:15:00Z",
    "last_message_at": "2025-12-01T10:15:05Z",
    "message_count": 2,
    "metadata": {}
  },
  "messages": [ /* array of messages */ ],
  "total_messages": 2
}
```

#### GET `/api/v1/messages/{message_id}`
**Get a single message by ID**

Response: Single message object

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://youthai:youthai@localhost:5432/youthai

# Service Configuration
SERVICE_NAME=message-service
API_PORT=8007
LOG_LEVEL=INFO

# External Services (for future safety integration)
TOPIC_CLASSIFIER_URL=http://localhost:8004
CONSENT_SERVICE_URL=http://localhost:8006

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8001"]
```

---

## Running the Service

### Local Development

```bash
# Install dependencies
cd services/message-service
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://youthai:youthai@localhost:5432/youthai"
export API_PORT=8007

# Run the service
python -m app.main
```

Service will start on `http://localhost:8007`

### Docker

```bash
# Build
docker build -t message-service .

# Run
docker run -p 8007:8007 \
  -e DATABASE_URL="postgresql+asyncpg://youthai:youthai@host.docker.internal:5432/youthai" \
  message-service
```

### Docker Compose

```bash
# Start message service (and dependencies)
docker-compose up message-service
```

---

## Usage Examples

### Complete Chat Flow

```python
import httpx

BASE_URL = "http://localhost:8007/api/v1"
teen_id = "550e8400-e29b-41d4-a716-446655440000"

async with httpx.AsyncClient() as client:
    # 1. Create a new conversation
    response = await client.post(
        f"{BASE_URL}/conversations",
        json={"teen_id": teen_id, "title": "Math Help"}
    )
    conversation = response.json()
    conv_id = conversation["id"]

    # 2. Add user message
    await client.post(
        f"{BASE_URL}/conversations/{conv_id}/messages",
        json={"role": "user", "content": "Help me solve 2x + 5 = 15"}
    )

    # 3. Add assistant response
    await client.post(
        f"{BASE_URL}/conversations/{conv_id}/messages",
        json={"role": "assistant", "content": "Let's solve this step by step..."}
    )

    # 4. Get conversation with all messages
    response = await client.get(
        f"{BASE_URL}/conversations/{conv_id}/with-messages"
    )
    data = response.json()
    print(f"Conversation: {data['conversation']['title']}")
    print(f"Messages: {len(data['messages'])}")

    # 5. List all conversations for teen
    response = await client.get(
        f"{BASE_URL}/teens/{teen_id}/conversations",
        params={"status": "active", "limit": 10}
    )
    conversations = response.json()
    print(f"Total conversations: {len(conversations)}")
```

### TypeScript/JavaScript (Frontend)

```typescript
const BASE_URL = 'http://localhost:8007/api/v1';
const teenId = '550e8400-e29b-41d4-a716-446655440000';

// Create conversation
const response = await fetch(`${BASE_URL}/conversations`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    teen_id: teenId,
    title: 'Math Help'
  })
});
const conversation = await response.json();

// Add message
await fetch(`${BASE_URL}/conversations/${conversation.id}/messages`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    role: 'user',
    content: 'Help me solve 2x + 5 = 15'
  })
});

// Get messages
const messagesResponse = await fetch(
  `${BASE_URL}/conversations/${conversation.id}/messages`
);
const messages = await messagesResponse.json();
```

---

## Integration with Other Services

### Topic Classification Integration (Future)

When a user message is created, the service can integrate with the Topic Classifier service:

```python
# After creating message
message = await msg_repo.create(message)

# Call topic classifier
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{settings.TOPIC_CLASSIFIER_URL}/api/v1/classify/",
        json={
            "message": message.content,
            "age_group": "13-14"
        }
    )
    classification = response.json()

    # Update message with classification
    message.set_topic_classification(
        tier=TopicTier(classification["tier"]),
        categories=classification["categories"],
        confidence=classification["confidence"]
    )
    await msg_repo.update(message)
```

### Consent Check Integration (Future)

Before allowing messages in a conversation, check consent:

```python
# Before creating message
async with httpx.AsyncClient() as client:
    response = await client.get(
        f"{settings.CONSENT_SERVICE_URL}/api/v1/consent/status/{teen_id}/{supervisor_id}"
    )
    status = response.json()

    if not status["has_active_consent"]:
        raise HTTPException(
            status_code=403,
            detail="Parental consent required"
        )
```

---

## Testing

### Manual API Testing

```bash
# Health check
curl http://localhost:8007/health

# Create conversation
curl -X POST http://localhost:8007/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "teen_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Math Help"
  }'

# Add message (use conversation_id from above)
curl -X POST http://localhost:8007/api/v1/conversations/{id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": "Help me with algebra"
  }'

# Get messages
curl http://localhost:8007/api/v1/conversations/{id}/messages
```

### Interactive API Documentation

Open http://localhost:8007/docs for Swagger UI with interactive testing

---

## Domain Logic

### Conversation Entity

**Business Rules:**
- Conversations can only be created with status "active"
- Archived conversations can be restored to active
- Deleted conversations cannot be restored
- Messages can only be added to active conversations
- Message count is automatically updated when messages are added
- Title is limited to 200 characters

**Methods:**
- `add_message()` - Increment count, update timestamps
- `set_title(title)` - Update conversation title
- `archive()` - Move to archived status
- `restore()` - Restore from archived to active
- `delete()` - Soft delete conversation
- `can_add_messages()` - Check if messages can be added

### Message Entity

**Business Rules:**
- Messages are immutable once created (content cannot be changed)
- Role must be: user, assistant, or system
- Topic tier can be: tier_1, tier_2, tier_3, tier_4, or null
- Safety flags are stored as JSON for flexibility

**Methods:**
- `is_user_message()`, `is_assistant_message()`, `is_system_message()`
- `is_safe()` - Check if message has no blocking safety flags
- `needs_approval()` - Check if tier 2 or 3 (needs parental approval)
- `is_tier_4()` - Check if message is blocked (tier 4)
- `set_topic_classification()` - Set topic tier and categories
- `add_safety_flag()` - Add safety concern
- `mark_as_blocked()` - Mark message as blocked
- `get_preview()` - Get truncated content preview

---

## Performance Considerations

### Database Indexes

The service includes indexes on:
- `conversations.teen_id` - Fast lookup of teen's conversations
- `conversations.status` - Filter by status
- `conversations.last_message_at` - Sort by recent activity
- `messages.conversation_id` - Fast message retrieval
- `messages.created_at` - Chronological ordering
- `messages.topic_tier` - Safety queries

### Pagination

All list endpoints support pagination:
- Default limits: 50 conversations, 100 messages
- Use `limit` and `offset` parameters
- Messages ordered by `created_at ASC` (oldest first)
- Conversations ordered by `last_message_at DESC` (most recent first)

### Caching (Future Enhancement)

Consider Redis caching for:
- Recent conversations (last 10 for each teen)
- Recent messages (last 50 in each conversation)
- Conversation metadata (title, message count)

---

## Security

### Data Protection
- All database connections use SSL in production
- Messages stored in plaintext (PII removed by PII service before storage)
- Safety metadata stored for audit purposes
- Soft delete preserves data for compliance

### Access Control (Future)
- Validate teen_id matches authenticated user
- Check parental consent before allowing message creation
- Supervisors can view conversation history
- Rate limiting on message creation

---

## Future Enhancements

### Phase 2
- [ ] Real-time WebSocket support for live chat
- [ ] Message search (full-text search)
- [ ] Message reactions/annotations
- [ ] Conversation sharing with supervisors
- [ ] Export conversation to PDF/text

### Phase 3
- [ ] Message editing (with edit history)
- [ ] Message deletion (soft delete)
- [ ] Conversation templates
- [ ] Bulk message operations
- [ ] Advanced filtering (by topic, date range, safety tier)

---

## Troubleshooting

### Messages not appearing

**Problem:** Messages created but not showing up

**Solutions:**
1. Check conversation status (must be "active")
2. Check pagination parameters (limit/offset)
3. Verify conversation_id is correct
4. Check database connection

### Conversation count not updating

**Problem:** message_count stays at 0

**Solution:** Ensure `conversation.add_message()` is called after creating message

### Database connection errors

**Problem:** Cannot connect to PostgreSQL

**Solutions:**
1. Verify `DATABASE_URL` is correct
2. Check PostgreSQL is running
3. Ensure database "youthai" exists
4. Check network connectivity

---

## Contributing

When adding features to the message service:

1. **Follow Clean Architecture:** Keep domain logic separate from infrastructure
2. **Write Tests:** Add unit tests for entities, integration tests for API
3. **Update Documentation:** Update this README with new endpoints/features
4. **Database Migrations:** Use Alembic for schema changes

---

**Created:** December 1, 2025
**Status:** ✅ Complete and ready for integration
**Dependencies:** PostgreSQL
