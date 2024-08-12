import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
    aws_glue as glue,
)
from constructs import Construct


class EcrScanLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        stack_name = self.stack_name.lower()
        bucket_name = f"{stack_name}-ecr-scan-results-rbmh-mzm"

        # Try to use an existing bucket, create a new one if it doesn't exist
        try:
            bucket = s3.Bucket.from_bucket_name(
                self, "EcrScanResultsBucket", bucket_name
            )
        except:
            bucket = s3.Bucket(
                self,
                "EcrScanResultsBucket",
                bucket_name=bucket_name,
                removal_policy=cdk.RemovalPolicy.RETAIN,
                auto_delete_objects=False,
            )

        # Create Lambda function
        lambda_function = _lambda.Function(
            self,
            "EcrScanLambdaFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={"BUCKET_NAME": bucket.bucket_name},
        )

        # Grant Lambda function permissions
        bucket.grant_write(lambda_function)
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["securityhub:BatchImportFindings"], resources=["*"]
            )
        )

        # Create EventBridge rule
        rule = events.Rule(
            self,
            "EcrScanCompletionRule",
            event_pattern=events.EventPattern(
                source=["aws.ecr"],
                detail_type=["ECR Image Scan"],
                detail={"scan-status": ["COMPLETE"]},
            ),
        )

        # Add Lambda function as target for the EventBridge rule
        rule.add_target(targets.LambdaFunction(lambda_function))

        # Create Glue database
        glue_database = glue.CfnDatabase(
            self,
            "EcrScanDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=f"{stack_name}_ecr_scan_db"
            ),
        )

        # Create Glue table for CSV data
        glue_table = glue.CfnTable(
            self,
            "EcrScanTable",
            database_name=glue_database.ref,
            catalog_id=self.account,
            table_input=glue.CfnTable.TableInputProperty(
                name="ecr_scan_results",
                table_type="EXTERNAL_TABLE",
                parameters={
                    "classification": "csv",
                    "typeOfData": "file",
                    "delimiter": ",",
                    "skip.header.line.count": "1",
                },
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    location=f"s3://{bucket.bucket_name}/",
                    input_format="org.apache.hadoop.mapred.TextInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.apache.hadoop.hive.serde2.OpenCSVSerde",
                        parameters={
                            "separatorChar": ",",
                            "quoteChar": '"',
                            "escapeChar": "\\",
                        },
                    ),
                    columns=[
                        glue.CfnTable.ColumnProperty(name="version", type="string"),
                        glue.CfnTable.ColumnProperty(name="id", type="string"),
                        glue.CfnTable.ColumnProperty(name="detail_type", type="string"),
                        glue.CfnTable.ColumnProperty(name="source", type="string"),
                        glue.CfnTable.ColumnProperty(name="account", type="string"),
                        glue.CfnTable.ColumnProperty(name="time", type="string"),
                        glue.CfnTable.ColumnProperty(name="region", type="string"),
                        glue.CfnTable.ColumnProperty(name="resources", type="string"),
                        glue.CfnTable.ColumnProperty(
                            name="repository_name", type="string"
                        ),
                        glue.CfnTable.ColumnProperty(
                            name="image_digest", type="string"
                        ),
                        glue.CfnTable.ColumnProperty(name="scan_status", type="string"),
                        glue.CfnTable.ColumnProperty(
                            name="severity_undefined", type="int"
                        ),
                        glue.CfnTable.ColumnProperty(name="severity_low", type="int"),
                        glue.CfnTable.ColumnProperty(
                            name="severity_medium", type="int"
                        ),
                        glue.CfnTable.ColumnProperty(name="severity_high", type="int"),
                        glue.CfnTable.ColumnProperty(
                            name="severity_critical", type="int"
                        ),
                        glue.CfnTable.ColumnProperty(name="image_tags", type="string"),
                    ],
                ),
            ),
        )


app = cdk.App()
EcrScanLambdaStack(app, "EcrScanLambdaStack")
app.synth()
