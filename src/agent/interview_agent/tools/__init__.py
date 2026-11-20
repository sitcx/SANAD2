"""Interview Agent tools.

Each tool is a normal Python function (the graph calls it directly) plus a LangChain
StructuredTool whose args_schema lists its parameters, types and which are required.
See a tool's parameters with:  compose_sentence_tool.args_schema.model_json_schema()

| Tool             | Required parameters             | Optional  | Returns                         |
|------------------|---------------------------------|-----------|---------------------------------|
| speech_to_text   | text_or_audio                   |           | question text                   |
| recognize_sign   | keypoint_segments               | top_k=5   | per sign: [{label_ar, score}]   |
| compose_sentence | candidate_words, last_question  |           | [3 Arabic sentences]            |
| call_interpreter | session_id, reason              |           | {session_id, reason, steps}     |
"""
from .call_interpreter import call_interpreter, call_interpreter_tool
from .compose_sentence import compose_sentence, compose_sentence_tool
from .recognize_sign import recognize_sign, recognize_sign_tool
from .speech_to_text import speech_to_text, speech_to_text_tool

TOOLS = [speech_to_text_tool, recognize_sign_tool, compose_sentence_tool, call_interpreter_tool]

__all__ = ["TOOLS", "call_interpreter", "call_interpreter_tool", "compose_sentence", "compose_sentence_tool",
           "recognize_sign", "recognize_sign_tool", "speech_to_text", "speech_to_text_tool"]
