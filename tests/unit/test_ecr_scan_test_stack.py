import aws_cdk as core
import aws_cdk.assertions as assertions

from ecr_scan_test.ecr_scan_test_stack import EcrScanTestStack

# example tests. To run these tests, uncomment this file along with the example
# resource in ecr_scan_test/ecr_scan_test_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = EcrScanTestStack(app, "ecr-scan-test")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
