from pyparsing import Dict
from typing import Optional, Dict, Union
import uuid
from datetime import datetime, timezone

data = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

id = uuid.uuid4()

class Sampledata:
    def get_sample(self)-> Dict[str, Optional[Union[str, int, float]]]:
        return {
            "assignee": None,
            "board_id": None,
            "completed_at": None,
            "created_at": str(data),
            "description": "Tarefa criada via flowbox",
            "duedate": None,
            "external_ref": None,
            "file_url": "https://drive.google.com/file/d/1C6j2RnGD6b5ZMAG4TaTCC2aHvfWDeEfB/view?usp=drivesdk",
            "id": str(id),
            "priority": "Média",
            "raw_metadata": None,
            "source": None,
            "status": "Pendentes",
            "title": "Tarefa vinda do flowbox",
            "updated_at": None,
            "user_id": "b07c83a9-6903-4e02-8e4c-46fd8d50acd7",
        }
    
    def get_sample_log(self):
        return {
            "action": "create_task",
            "created_at": str(data),
            "details": f"Tarefa criada: {{'id': {str(id)}}}",
            "metadata": None,
            "user_id": "b07c83a9-6903-4e02-8e4c-46fd8d50acd7",
        }