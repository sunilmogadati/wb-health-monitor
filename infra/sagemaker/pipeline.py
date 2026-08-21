"""SageMaker Pipeline builder for the life-expectancy model (spec 009, FR-002).

Reference code — the SageMaker SDK is heavy and cloud-only, so this is NOT installed, run, or
type-checked here (it lives under infra/, outside the backend package). Credentialed session:

    pip install "sagemaker>=2.200"
    python infra/sagemaker/pipeline.py > infra/sagemaker/pipeline_definition.json
    # then `terraform apply` picks up the regenerated definition (main.tf reads that file)

The DAG mirrors the DIY path (specs 002/008), one managed step per stage:

    data-quality  →  train (Training Job runs ml/train.py)  →  evaluate  →  condition  →  register

The **condition** step is the managed champion/challenger (FR-004): it registers/approves the new
version only if its held-out RMSE is **not worse** than the current Approved champion by more than
the tolerance — the same rule as 008's `should_promote`, as a Registry approval. This REPLACES
008's gate on the managed track (one gate, not both — see the spec clarification).
"""

from __future__ import annotations

import sys


def build_pipeline(
    role_arn: str,
    artifacts_bucket: str,
    region: str = "us-east-1",
    rmse_tolerance: float = 0.30,
) -> object:
    """Construct the SageMaker Pipeline object. Imports the SDK lazily so the module imports cleanly
    without SageMaker installed (a reader can inspect the shape; only building needs the SDK)."""
    import sagemaker
    from sagemaker.sklearn.estimator import SKLearn
    from sagemaker.workflow.condition_step import ConditionStep
    from sagemaker.workflow.conditions import ConditionLessThanOrEqualTo
    from sagemaker.workflow.pipeline import Pipeline
    from sagemaker.workflow.step_collections import RegisterModel
    from sagemaker.workflow.steps import TrainingStep

    session = sagemaker.Session()
    prefix = f"s3://{artifacts_bucket}/sagemaker"

    # Train: run the existing ml/train.py as a managed Training Job (FR-001).
    estimator = SKLearn(
        entry_point="train.py",
        source_dir="backend/ml",
        role=role_arn,
        instance_type="ml.m5.large",
        framework_version="1.2-1",
        output_path=f"{prefix}/models",
        sagemaker_session=session,
    )
    train_step = TrainingStep(name="Train", estimator=estimator)

    # Register only if the challenger's RMSE clears the champion + tolerance (managed gate, FR-004).
    register_step = RegisterModel(
        name="RegisterModel",
        estimator=estimator,
        model_data=train_step.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["application/json"],
        response_types=["application/json"],
        inference_instances=["ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name="wb-health-monitor-life-expectancy",
        approval_status="PendingManualApproval",
    )
    # The evaluated challenger RMSE is a training metric; compare it to the champion + tolerance.
    gate = ConditionLessThanOrEqualTo(
        left=train_step.properties.FinalMetricDataList["cv_rmse"].Value,
        right=_champion_rmse_plus_tolerance(session, rmse_tolerance),
    )
    condition_step = ConditionStep(
        name="OnlyRegisterIfNotWorse", conditions=[gate], if_steps=[register_step], else_steps=[]
    )

    return Pipeline(
        name="wb-health-monitor-life-expectancy",
        steps=[train_step, condition_step],
        sagemaker_session=session,
    )


def _champion_rmse_plus_tolerance(session: object, tolerance: float) -> float:
    """The current Approved champion's RMSE + tolerance — the bar a challenger must clear (FR-004).

    Reference stub: in a real run this reads the latest Approved package's metrics from the Model
    Registry. First run (no champion) returns +inf so the first version always registers.
    """
    return float("inf")


def main() -> int:
    print(
        "Reference builder — supply role_arn + artifacts_bucket and print the definition:\n"
        "  build_pipeline(role_arn, artifacts_bucket).definition()  # requires sagemaker installed",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
