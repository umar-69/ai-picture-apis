# Dataset Training Status API

## Overview
This API allows you to update the training status of a dataset, marking it as either "trained" or "not_trained". This is useful for tracking whether a user has completed training on a particular dataset from the frontend.

## Endpoint

### Update Dataset Training Status
**PATCH** `/ai/dataset/{dataset_id}/training-status`

Updates the training status flag for a specific dataset.

#### Request

**URL Parameters:**
- `dataset_id` (string, required): The UUID of the dataset to update

**Form Data:**
- `training_status` (string, required): Must be either `"trained"` or `"not_trained"`

**Headers:**
- `Authorization: Bearer <token>` (optional): User authentication token

#### Response

**Success (200 OK):**
```json
{
  "success": true,
  "dataset_id": "123e4567-e89b-12d3-a456-426614174000",
  "training_status": "trained",
  "message": "Dataset training status updated to 'trained'"
}
```

**Error Responses:**

- **400 Bad Request**: Invalid training_status value
```json
{
  "detail": "training_status must be either 'trained' or 'not_trained'"
}
```

- **404 Not Found**: Dataset doesn't exist
```json
{
  "detail": "Dataset not found"
}
```

- **403 Forbidden**: User doesn't own the dataset
```json
{
  "detail": "You don't have permission to update this dataset"
}
```

## Usage Examples

### JavaScript/Fetch

```javascript
// Mark dataset as trained
const datasetId = "123e4567-e89b-12d3-a456-426614174000";

const formData = new FormData();
formData.append("training_status", "trained");

const response = await fetch(
  `https://ai-picture-apis.onrender.com/ai/dataset/${datasetId}/training-status`,
  {
    method: "PATCH",
    headers: {
      "Authorization": `Bearer ${userToken}` // Optional
    },
    body: formData
  }
);

const result = await response.json();
console.log(result);
// { success: true, dataset_id: "...", training_status: "trained", message: "..." }
```

### cURL

```bash
# Mark as trained
curl -X PATCH \
  "https://ai-picture-apis.onrender.com/ai/dataset/123e4567-e89b-12d3-a456-426614174000/training-status" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "training_status=trained"

# Mark as not trained
curl -X PATCH \
  "https://ai-picture-apis.onrender.com/ai/dataset/123e4567-e89b-12d3-a456-426614174000/training-status" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "training_status=not_trained"
```

### Python

```python
import requests

dataset_id = "123e4567-e89b-12d3-a456-426614174000"
url = f"https://ai-picture-apis.onrender.com/ai/dataset/{dataset_id}/training-status"

data = {"training_status": "trained"}
headers = {"Authorization": f"Bearer {user_token}"}  # Optional

response = requests.patch(url, data=data, headers=headers)
result = response.json()
print(result)
```

## Database Schema

The `datasets` table now includes a `training_status` column:

```sql
ALTER TABLE datasets 
ADD COLUMN training_status TEXT DEFAULT 'not_trained' 
CHECK (training_status IN ('not_trained', 'trained'));
```

**Column Details:**
- **Type**: TEXT
- **Default**: `'not_trained'`
- **Constraint**: Must be either `'not_trained'` or `'trained'`

## Frontend Integration

### When to Use

1. **After Dataset Upload**: When user finishes uploading images to a dataset
2. **Training Button Click**: When user clicks "Mark as Trained" button
3. **Status Toggle**: When user wants to change training status

### Example React Component

```jsx
function DatasetTrainingButton({ datasetId, currentStatus, onStatusChange }) {
  const [loading, setLoading] = useState(false);
  
  const toggleTrainingStatus = async () => {
    setLoading(true);
    
    const newStatus = currentStatus === "trained" ? "not_trained" : "trained";
    const formData = new FormData();
    formData.append("training_status", newStatus);
    
    try {
      const response = await fetch(
        `https://ai-picture-apis.onrender.com/ai/dataset/${datasetId}/training-status`,
        {
          method: "PATCH",
          headers: {
            "Authorization": `Bearer ${localStorage.getItem("token")}`
          },
          body: formData
        }
      );
      
      const result = await response.json();
      
      if (result.success) {
        onStatusChange(newStatus);
        toast.success(`Dataset marked as ${newStatus}`);
      }
    } catch (error) {
      toast.error("Failed to update training status");
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <button 
      onClick={toggleTrainingStatus}
      disabled={loading}
      className={currentStatus === "trained" ? "btn-success" : "btn-default"}
    >
      {loading ? "Updating..." : currentStatus === "trained" ? "✓ Trained" : "Mark as Trained"}
    </button>
  );
}
```

## Key Features

✅ **Simple Status Flag**: Easy to understand "trained" vs "not_trained" states
✅ **Anonymous Support**: Works with or without authentication
✅ **Ownership Validation**: Checks user permissions if authenticated
✅ **Database Constraint**: Ensures only valid status values
✅ **Frontend-Driven**: User controls when to mark datasets as trained
✅ **Non-Destructive**: Doesn't modify existing `/ai/dataset/analyze` endpoint

## Use Cases

1. **Training Workflow Tracking**: Track which datasets have been used for training
2. **UI State Management**: Show different UI based on training status
3. **Analytics**: Monitor how many datasets users are training with
4. **Workflow Completion**: Mark milestones in the dataset preparation process

## Notes

- The training status is a simple flag and doesn't perform any actual training
- It's managed entirely by the frontend based on user actions
- Anonymous users can update status (useful for free trial workflows)
- The status persists in the database for future reference
