import json
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from langchain_anthropic import ChatAnthropic

load_dotenv()

with open('run_summary.json') as f:
    summary = json.load(f)


class ModelResult(BaseModel):
    model_name: str = Field(description="Name of the model")
    r2_score: float = Field(description="R-squared score on the test set")
    rmse: float = Field(description="Root mean squared error, in years of life expectancy")
    verdict: str = Field(description="One short sentence judging this model's performance")


class ProjectReport(BaseModel):
    executive_summary: str = Field(description="2-3 sentence plain-language summary for a non-technical stakeholder")
    best_model: str = Field(description="Name of the best performing model")
    best_model_justification: str = Field(description="Why this model won, in plain language")
    model_results: List[ModelResult] = Field(description="Structured results for every model tested")
    top_predictive_feature: str = Field(description="The single feature that mattered most to the best model")
    key_findings: List[str] = Field(description="3-5 bullet-point findings a manager could read directly")
    recommendation: str = Field(description="One concrete recommendation for next steps")


llm = ChatAnthropic(model="claude-opus-5")
structured_llm = llm.with_structured_output(ProjectReport)

prompt = (
    "Generate a professional project report based on this model comparison data. "
    "Only use the data provided, do not invent numbers.\n\n"
    + json.dumps(summary, indent=2)
)

report = structured_llm.invoke(prompt)

print("\n" + "=" * 60)
print("PROJECT REPORT: LIFE EXPECTANCY PREDICTION")
print("=" * 60)

print("\nEXECUTIVE SUMMARY")
print(report.executive_summary)

print("\nBEST MODEL:", report.best_model)
print(report.best_model_justification)

print("\nMODEL COMPARISON")
for m in report.model_results:
    print(f"  {m.model_name:<20} R2: {m.r2_score:.3f}   RMSE: {m.rmse:.2f}")
    print(f"  {'':<20} {m.verdict}")

print("\nTOP PREDICTIVE FEATURE:", report.top_predictive_feature)

print("\nKEY FINDINGS")
for i, finding in enumerate(report.key_findings, 1):
    print(f"  {i}. {finding}")

print("\nRECOMMENDATION")
print(report.recommendation)
print("\n" + "=" * 60)

with open('final_report.json', 'w') as f:
    f.write(report.model_dump_json(indent=2))

print('\nSaved final_report.json')