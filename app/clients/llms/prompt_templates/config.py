from enum import Enum


class LLMTasks(Enum):
    DOCUMENTS_SUMMARIZATION = "documents_summarization"
    ONLINE_SEARCH_SUMMARIZATION = "online_search_summarization"
    FINAL_REPORT_GENERATION = "final_report_generation"


class PromptTypes(Enum):
    SYSTEM_PROMPT = "system_prompt"
    TASK_PROMPT = "task_prompt"
    FOOTER_PROMPT = "footer_prompt"