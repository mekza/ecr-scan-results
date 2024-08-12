import json
import boto3
import csv
from io import StringIO
import os
from datetime import datetime
import uuid

s3 = boto3.client("s3")
securityhub = boto3.client("securityhub")


def handler(event, context):
    bucket_name = os.environ["BUCKET_NAME"]

    # Convert the event to a dictionary if it's not already
    if isinstance(event, str):
        event = json.loads(event)

    # Flatten the JSON structure for CSV
    flattened_data = flatten_event(event)

    # Create and upload CSV
    create_and_upload_csv(flattened_data, bucket_name)

    # Send findings to Security Hub
    send_to_security_hub(event)

    return {"statusCode": 200, "body": json.dumps("Scan result processed successfully")}


def flatten_event(event):
    return {
        "version": event["version"],
        "id": event["id"],
        "detail_type": event["detail-type"],
        "source": event["source"],
        "account": event["account"],
        "time": event["time"],
        "region": event["region"],
        "resources": ",".join(event["resources"]),
        "repository_name": event["detail"]["repository-name"],
        "image_digest": event["detail"]["image-digest"],
        "scan_status": event["detail"]["scan-status"],
        "severity_undefined": event["detail"]["finding-severity-counts"].get(
            "UNDEFINED", 0
        ),
        "severity_low": event["detail"]["finding-severity-counts"].get("LOW", 0),
        "severity_medium": event["detail"]["finding-severity-counts"].get("MEDIUM", 0),
        "severity_high": event["detail"]["finding-severity-counts"].get("HIGH", 0),
        "severity_critical": event["detail"]["finding-severity-counts"].get(
            "CRITICAL", 0
        ),
        "image_tags": "|".join(event["detail"]["image-tags"]),
    }


def create_and_upload_csv(data, bucket_name):
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=data.keys())
    writer.writeheader()
    writer.writerow(data)

    file_name = f"ecr-scan-{data['repository_name']}-{data['image_digest'][:12]}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"

    s3.put_object(Bucket=bucket_name, Key=file_name, Body=csv_buffer.getvalue())


def send_to_security_hub(event):
    repository_arn = event["resources"][0]
    image_digest = event["detail"]["image-digest"]
    repository_name = event["detail"]["repository-name"]
    account_id = event["account"]
    region = event["region"]

    # Create finding for Container Image
    image_finding = create_finding(
        account_id,
        region,
        f"{repository_arn}/{image_digest}",
        f"ECR Scan Results for Image: {image_digest}",
        f"Vulnerabilities found in Container Image: {image_digest}",
        event["detail"]["finding-severity-counts"],
        [
            {
                "Type": "AwsEcrContainerImage",
                "Id": f"{repository_arn}/{image_digest}",
                "Details": {
                    "AwsEcrContainerImage": {
                        "RepositoryName": repository_name,
                        "ImageDigest": image_digest,
                        "ImageTags": event["detail"]["image-tags"],
                    }
                },
            }
        ],
        event["time"],
        event["detail"].get("findings", []),
    )

    # Send finding to Security Hub
    securityhub.batch_import_findings(Findings=[image_finding])


def create_finding(
    account_id,
    region,
    resource_id,
    title,
    description,
    severity_counts,
    resources,
    timestamp,
    findings,
):
    severity = get_severity(severity_counts)

    vulnerability_details = []
    for finding in findings:
        vulnerability_details.append(
            {
                "Name": finding.get("name", "Unknown"),
                "Severity": finding.get("severity", "UNKNOWN"),
                "Description": finding.get("description", "No description provided"),
                "PackageName": finding.get("packageName", "Unknown"),
                "PackageVersion": finding.get("packageVersion", "Unknown"),
            }
        )

    return {
        "SchemaVersion": "2018-10-08",
        "Id": f"{resource_id}/ecr-scan-{uuid.uuid4()}",
        "ProductArn": f"arn:aws:securityhub:{region}:{account_id}:product/{account_id}/default",
        "GeneratorId": "ecr-scan-lambda",
        "AwsAccountId": account_id,
        "Types": ["Software and Configuration Checks/Vulnerabilities/CVE"],
        "CreatedAt": timestamp,
        "UpdatedAt": timestamp,
        "Severity": {"Label": severity},
        "Title": title,
        "Description": description,
        "Resources": resources,
        "ProductFields": {"ProductName": "ECR Scan"},
        "RecordState": "ACTIVE",
        "Vulnerabilities": vulnerability_details,
        "FindingProviderFields": {
            "Severity": {"Label": severity, "Original": json.dumps(severity_counts)},
            "Types": ["Vulnerabilities"],
        },
    }


def get_severity(severity_counts):
    if severity_counts.get("CRITICAL", 0) > 0:
        return "CRITICAL"
    elif severity_counts.get("HIGH", 0) > 0:
        return "HIGH"
    elif severity_counts.get("MEDIUM", 0) > 0:
        return "MEDIUM"
    elif severity_counts.get("LOW", 0) > 0:
        return "LOW"
    else:
        return "INFORMATIONAL"
