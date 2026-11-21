"""Job Agent tools.

Each tool is a normal Python function (the graph calls it directly) plus a LangChain
StructuredTool whose args_schema lists its parameters, types and which are required.
See a tool's parameters with:  read_cv_tool.args_schema.model_json_schema()

| Tool        | Required parameters | Optional        | Returns                                   |
|-------------|---------------------|-----------------|-------------------------------------------|
| read_cv     | cv_file             |                 | {skills, major, experience_years, city, ats_profile, reading} |
| search_jobs | profile             | widen=False     | [job, ...] from jobs.json + postings (company + found jobs)   |
| score_job   | profile, job        | cv_text=""      | {job_id, match, city, matched_skills, missing_skills, reason} |

read_cv uses the ATS reader in ../ats (teammate's CV agent, ported); score_job uses its weighted matcher;
the job search agent (../search) adds real postings from public sources and Claude web search.
"""
from .read_cv import read_cv, read_cv_tool
from .score_job import score_job, score_job_tool
from .search_jobs import search_jobs, search_jobs_tool

TOOLS = [read_cv_tool, search_jobs_tool, score_job_tool]

__all__ = ["TOOLS", "read_cv", "read_cv_tool", "score_job", "score_job_tool", "search_jobs", "search_jobs_tool"]
