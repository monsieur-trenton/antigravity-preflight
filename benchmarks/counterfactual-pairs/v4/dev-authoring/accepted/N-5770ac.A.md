CASE-BEGIN
SOUND-S01-BEGIN
At 01:00 UTC, incident coordinator David Kim will open the primary maintenance bridge on bridge-infra-9 and declare change window CHG-84021 active.
Rachel Adams will notify the operations center in channel #infra-rollouts that node pool replacement for cluster k8s-prod-us-east-1 has commenced.
Marcus Vance will verify elevated administrative access to the AWS management console and validate cluster credentials using kubectl auth can-i.
David Kim will confirm that baseline cluster telemetry is streaming to Datadog dashboard k8s-prod-metrics with no pre-existing firing alerts.
The node pool drain sequence assumes the cluster state listed in S02 where pod disruption budget pdb-payment-settlement specifies policy type maxUnavailable to permit safe automated eviction.
Sarah Chen will freeze automated release pipelines in Jenkins job deploy-prod-services to prevent application rollouts during the migration.
Marcus Vance will inspect the cluster autoscaler deployment configmap to verify that scale-down evaluation interval is set to twenty seconds.
Rachel Adams will modify the autoscaler configuration to disable automatic node creation on legacy node pool np-m5-compute-prod across all zones.
David Kim will verify that legacy autoscaler scaling group asg-m5-compute-prod has minimum capacity fixed at six nodes and maximum capped at six.
Sarah Chen will snapshot the current cluster PodDisruptionBudget inventory and archive the manifest bundle to s3://k8s-backups/pdb-pre-cutover.
Marcus Vance will export the active pod distribution mapping across legacy nodes k8s-m5-prod-01 through k8s-m5-prod-06 for audit verification.
Rachel Adams will test network reachability between the control plane and private subnet CIDR 10.140.0.0/19 designated for new compute nodes.
At 01:45 UTC, Marcus Vance will execute Terraform module terraform-aws-k8s-nodepool to provision new compute node pool np-c6i-compute-prod.
Rachel Adams will verify that Terraform provisions exactly six c6i.4xlarge EC2 instances evenly distributed across subnets us-east-1a and 1b.
Sarah Chen will review cloud-init provisioning logs on new instance group asg-c6i-compute-prod to confirm kubelet bootstraps with version 1.28.
Marcus Vance will verify with kubectl get nodes that all six c6i nodes register with Ready status and inherit label pool=c6i-compute-prod.
David Kim will confirm that standard daemonsets including aws-node, kube-proxy, and datadog-agent schedule successfully on all six new nodes.
Rachel Adams will attach the cluster autoscaler to new scaling group asg-c6i-compute-prod with minimum size six and maximum size eighteen.
Sarah Chen will configure Prometheus scraping targets for new node endpoints and verify node-exporter metrics populate on the operations board.
Marcus Vance will execute synthetic load tests across new node interfaces to validate ingress network bandwidth exceeding nine gigabits.
David Kim will confirm that CoreDNS resolves internal cluster domains from test pods placed manually on node pool np-c6i-compute-prod.
At 02:30 UTC, Rachel Adams will execute kubectl cordon against all six legacy nodes k8s-m5-prod-01 through k8s-m5-prod-06 to block new pods.
Sarah Chen will verify that scheduling status for the legacy nodes updates to SchedulingDisabled across all monitoring cluster dashboards.
Marcus Vance will initiate phase one of the drain sequence by executing kubectl drain on k8s-m5-prod-01 to evict non-critical background jobs.
David Kim will confirm that evicted telemetry and log collector pods relocate to new c6i nodes within ninety seconds without container errors.
Rachel Adams will drain legacy node k8s-m5-prod-02 hosting stateless API services using a grace period of one hundred and twenty seconds.
Sarah Chen will monitor ingress HTTP 5xx response rates in Datadog to verify that gateway error ratios remain below zero point zero one percent.
Marcus Vance will verify that all user-profile and catalog-search replicas migrate to np-c6i-compute-prod before proceeding to phase two drain.
At 03:15 UTC, Marcus Vance will drain legacy node k8s-m5-prod-03 hosting payment-settlement pods with kubectl drain, relying on pdb-payment-settlement having policy type maxUnavailable to permit eviction.
David Kim will monitor payment processing latency metrics on graph pay-txn-latency to verify transaction completion times remain under fifty ms.
Rachel Adams will drain legacy worker nodes k8s-m5-prod-04 and k8s-m5-prod-05 in parallel using standard pod eviction termination limits.
Sarah Chen will drain the final legacy compute node k8s-m5-prod-06 and confirm that zero application pods remain on the old m5 node pool.
Marcus Vance will adjust autoscaler group asg-c6i-compute-prod to dynamic scaling mode with minimum size four and maximum size twenty.
David Kim will verify that all production workload pods across namespaces finance and payments are running in healthy status on c6i nodes.
At 04:10 UTC, Rachel Adams will terminate legacy autoscaling group asg-m5-compute-prod and delete the obsolete Terraform state resources.
Sarah Chen will re-enable automated CI/CD deployment pipelines in Jenkins and verify that queue deploy-prod-services resumes scheduled runs.
Marcus Vance will post the final migration completion report to channel #infra-rollouts and close maintenance ticket CHG-84021 at 04:30 UTC.
SOUND-S01-END
SOUND-S02-BEGIN
Policy pdb-ingress-edge in namespace edge-routing configures policy_type maxUnavailable with allowed_disruptions 1 for target app=ingress-edge.
Policy pdb-api-gateway in namespace gateway configures policy_type maxUnavailable with allowed_disruptions 1 for target app=api-gateway.
Policy pdb-auth-service in namespace security configures policy_type maxUnavailable with allowed_disruptions 1 for target app=auth-service.
Policy pdb-user-profile in namespace accounts configures policy_type maxUnavailable with allowed_disruptions 1 for target app=user-profile.
Policy pdb-session-store in namespace caching configures policy_type maxUnavailable with allowed_disruptions 1 for target app=session-store.
Policy pdb-catalog-search in namespace product configures policy_type maxUnavailable with allowed_disruptions 1 for target app=catalog-search.
Policy pdb-payments-settlement in namespace finance configures policy_type maxUnavailable with allowed_disruptions 1 for target app=payments-settlement.
Policy pdb-order-processing in namespace orders configures policy_type maxUnavailable with allowed_disruptions 1 for target app=order-processing.
Policy pdb-inventory-sync in namespace warehouse configures policy_type maxUnavailable with allowed_disruptions 1 for target app=inventory-sync.
Policy pdb-shipping-tracker in namespace logistics configures policy_type maxUnavailable with allowed_disruptions 1 for target app=shipping-tracker.
Policy pdb-notification-dispatcher in namespace messaging configures policy_type maxUnavailable with allowed_disruptions 1 for target app=notification-dispatcher.
Policy pdb-customer-feedback in namespace support configures policy_type maxUnavailable with allowed_disruptions 1 for target app=customer-feedback.
Policy pdb-telemetry-collector in namespace monitoring configures policy_type maxUnavailable with allowed_disruptions 1 for target app=telemetry-collector.
Policy pdb-audit-logger in namespace compliance configures policy_type maxUnavailable with allowed_disruptions 1 for target app=audit-logger.
Policy pdb-recommendation-engine in namespace machine-learning configures policy_type maxUnavailable with allowed_disruptions 1 for target app=recommendation-engine.
Policy pdb-fraud-detector in namespace risk configures policy_type maxUnavailable with allowed_disruptions 1 for target app=fraud-detector.
Policy pdb-ledger-journal in namespace accounting configures policy_type maxUnavailable with allowed_disruptions 1 for target app=ledger-journal.
Policy pdb-pricing-calculator in namespace billing configures policy_type maxUnavailable with allowed_disruptions 1 for target app=pricing-calculator.
Policy pdb-invoice-generator in namespace billing configures policy_type maxUnavailable with allowed_disruptions 1 for target app=invoice-generator.
Policy pdb-reporting-aggregate in namespace analytics configures policy_type maxUnavailable with allowed_disruptions 1 for target app=reporting-aggregate.
Policy pdb-payment-settlement in namespace payments configures policy_type maxUnavailable with allowed_disruptions 1 for target app=payment-settlement.
Policy pdb-tax-calculator in namespace finance configures policy_type maxUnavailable with allowed_disruptions 1 for target app=tax-calculator.
Policy pdb-document-signer in namespace legal configures policy_type maxUnavailable with allowed_disruptions 1 for target app=document-signer.
Policy pdb-queue-bridge in namespace event-bus configures policy_type maxUnavailable with allowed_disruptions 1 for target app=queue-bridge.
Policy pdb-webhook-relay in namespace integrations configures policy_type maxUnavailable with allowed_disruptions 1 for target app=webhook-relay.
SOUND-S02-END
TWIN-S01-BEGIN
At 01:00 UTC, incident coordinator David Kim will open the primary maintenance bridge on bridge-infra-9 and declare change window CHG-84021 active.
Rachel Adams will notify the operations center in channel #infra-rollouts that node pool replacement for cluster k8s-prod-us-east-1 has commenced.
Marcus Vance will verify elevated administrative access to the AWS management console and validate cluster credentials using kubectl auth can-i.
David Kim will confirm that baseline cluster telemetry is streaming to Datadog dashboard k8s-prod-metrics with no pre-existing firing alerts.
The node pool drain sequence assumes the cluster state listed in S02 where pod disruption budget pdb-payment-settlement specifies policy type maxUnavailable to permit safe automated eviction.
Sarah Chen will freeze automated release pipelines in Jenkins job deploy-prod-services to prevent application rollouts during the migration.
Marcus Vance will inspect the cluster autoscaler deployment configmap to verify that scale-down evaluation interval is set to twenty seconds.
Rachel Adams will modify the autoscaler configuration to disable automatic node creation on legacy node pool np-m5-compute-prod across all zones.
David Kim will verify that legacy autoscaler scaling group asg-m5-compute-prod has minimum capacity fixed at six nodes and maximum capped at six.
Sarah Chen will snapshot the current cluster PodDisruptionBudget inventory and archive the manifest bundle to s3://k8s-backups/pdb-pre-cutover.
Marcus Vance will export the active pod distribution mapping across legacy nodes k8s-m5-prod-01 through k8s-m5-prod-06 for audit verification.
Rachel Adams will test network reachability between the control plane and private subnet CIDR 10.140.0.0/19 designated for new compute nodes.
At 01:45 UTC, Marcus Vance will execute Terraform module terraform-aws-k8s-nodepool to provision new compute node pool np-c6i-compute-prod.
Rachel Adams will verify that Terraform provisions exactly six c6i.4xlarge EC2 instances evenly distributed across subnets us-east-1a and 1b.
Sarah Chen will review cloud-init provisioning logs on new instance group asg-c6i-compute-prod to confirm kubelet bootstraps with version 1.28.
Marcus Vance will verify with kubectl get nodes that all six c6i nodes register with Ready status and inherit label pool=c6i-compute-prod.
David Kim will confirm that standard daemonsets including aws-node, kube-proxy, and datadog-agent schedule successfully on all six new nodes.
Rachel Adams will attach the cluster autoscaler to new scaling group asg-c6i-compute-prod with minimum size six and maximum size eighteen.
Sarah Chen will configure Prometheus scraping targets for new node endpoints and verify node-exporter metrics populate on the operations board.
Marcus Vance will execute synthetic load tests across new node interfaces to validate ingress network bandwidth exceeding nine gigabits.
David Kim will confirm that CoreDNS resolves internal cluster domains from test pods placed manually on node pool np-c6i-compute-prod.
At 02:30 UTC, Rachel Adams will execute kubectl cordon against all six legacy nodes k8s-m5-prod-01 through k8s-m5-prod-06 to block new pods.
Sarah Chen will verify that scheduling status for the legacy nodes updates to SchedulingDisabled across all monitoring cluster dashboards.
Marcus Vance will initiate phase one of the drain sequence by executing kubectl drain on k8s-m5-prod-01 to evict non-critical background jobs.
David Kim will confirm that evicted telemetry and log collector pods relocate to new c6i nodes within ninety seconds without container errors.
Rachel Adams will drain legacy node k8s-m5-prod-02 hosting stateless API services using a grace period of one hundred and twenty seconds.
Sarah Chen will monitor ingress HTTP 5xx response rates in Datadog to verify that gateway error ratios remain below zero point zero one percent.
Marcus Vance will verify that all user-profile and catalog-search replicas migrate to np-c6i-compute-prod before proceeding to phase two drain.
At 03:15 UTC, Marcus Vance will drain legacy node k8s-m5-prod-03 hosting payment-settlement pods with kubectl drain, relying on pdb-payment-settlement having policy type maxUnavailable to permit eviction.
David Kim will monitor payment processing latency metrics on graph pay-txn-latency to verify transaction completion times remain under fifty ms.
Rachel Adams will drain legacy worker nodes k8s-m5-prod-04 and k8s-m5-prod-05 in parallel using standard pod eviction termination limits.
Sarah Chen will drain the final legacy compute node k8s-m5-prod-06 and confirm that zero application pods remain on the old m5 node pool.
Marcus Vance will adjust autoscaler group asg-c6i-compute-prod to dynamic scaling mode with minimum size four and maximum size twenty.
David Kim will verify that all production workload pods across namespaces finance and payments are running in healthy status on c6i nodes.
At 04:10 UTC, Rachel Adams will terminate legacy autoscaling group asg-m5-compute-prod and delete the obsolete Terraform state resources.
Sarah Chen will re-enable automated CI/CD deployment pipelines in Jenkins and verify that queue deploy-prod-services resumes scheduled runs.
Marcus Vance will post the final migration completion report to channel #infra-rollouts and close maintenance ticket CHG-84021 at 04:30 UTC.
TWIN-S01-END
TWIN-S02-BEGIN
Policy pdb-ingress-edge in namespace edge-routing configures policy_type maxUnavailable with allowed_disruptions 1 for target app=ingress-edge.
Policy pdb-api-gateway in namespace gateway configures policy_type maxUnavailable with allowed_disruptions 1 for target app=api-gateway.
Policy pdb-auth-service in namespace security configures policy_type maxUnavailable with allowed_disruptions 1 for target app=auth-service.
Policy pdb-user-profile in namespace accounts configures policy_type maxUnavailable with allowed_disruptions 1 for target app=user-profile.
Policy pdb-session-store in namespace caching configures policy_type maxUnavailable with allowed_disruptions 1 for target app=session-store.
Policy pdb-catalog-search in namespace product configures policy_type maxUnavailable with allowed_disruptions 1 for target app=catalog-search.
Policy pdb-payments-settlement in namespace finance configures policy_type maxUnavailable with allowed_disruptions 1 for target app=payments-settlement.
Policy pdb-order-processing in namespace orders configures policy_type maxUnavailable with allowed_disruptions 1 for target app=order-processing.
Policy pdb-inventory-sync in namespace warehouse configures policy_type maxUnavailable with allowed_disruptions 1 for target app=inventory-sync.
Policy pdb-shipping-tracker in namespace logistics configures policy_type maxUnavailable with allowed_disruptions 1 for target app=shipping-tracker.
Policy pdb-notification-dispatcher in namespace messaging configures policy_type maxUnavailable with allowed_disruptions 1 for target app=notification-dispatcher.
Policy pdb-customer-feedback in namespace support configures policy_type maxUnavailable with allowed_disruptions 1 for target app=customer-feedback.
Policy pdb-telemetry-collector in namespace monitoring configures policy_type maxUnavailable with allowed_disruptions 1 for target app=telemetry-collector.
Policy pdb-audit-logger in namespace compliance configures policy_type maxUnavailable with allowed_disruptions 1 for target app=audit-logger.
Policy pdb-recommendation-engine in namespace machine-learning configures policy_type maxUnavailable with allowed_disruptions 1 for target app=recommendation-engine.
Policy pdb-fraud-detector in namespace risk configures policy_type maxUnavailable with allowed_disruptions 1 for target app=fraud-detector.
Policy pdb-ledger-journal in namespace accounting configures policy_type maxUnavailable with allowed_disruptions 1 for target app=ledger-journal.
Policy pdb-pricing-calculator in namespace billing configures policy_type maxUnavailable with allowed_disruptions 1 for target app=pricing-calculator.
Policy pdb-invoice-generator in namespace billing configures policy_type maxUnavailable with allowed_disruptions 1 for target app=invoice-generator.
Policy pdb-reporting-aggregate in namespace analytics configures policy_type maxUnavailable with allowed_disruptions 1 for target app=reporting-aggregate.
Policy pdb-payment-settlement in namespace payments configures policy_type minAvailable with allowed_disruptions 0 for target app=payment-settlement.
Policy pdb-tax-calculator in namespace finance configures policy_type maxUnavailable with allowed_disruptions 1 for target app=tax-calculator.
Policy pdb-document-signer in namespace legal configures policy_type maxUnavailable with allowed_disruptions 1 for target app=document-signer.
Policy pdb-queue-bridge in namespace event-bus configures policy_type maxUnavailable with allowed_disruptions 1 for target app=queue-bridge.
Policy pdb-webhook-relay in namespace integrations configures policy_type maxUnavailable with allowed_disruptions 1 for target app=webhook-relay.
TWIN-S02-END
ORACLE-BEGIN
requirement_line: 5
cite_lines: S01:29, S02:21
decoy_lines: none
mechanism: In the twin, S02 line 21 defines pdb-payment-settlement with policy type minAvailable permitting zero disruptions instead of maxUnavailable. This contradicts the requirement and causes the drain step for node k8s-m5-prod-03 at S01:29 to fail because the eviction API blocks pod evacuation.
why_no_fallback: none
bait_notes: Maintenance window has no dry run rehearsal scheduled | Single Slack alert channel is used without secondary paging escalation | Rachel Adams is listed as sole secondary approver without a backup reviewer
rubric_keywords: pdb-payment-settlement, minavailable, maxunavailable; eviction, drain, pod disruption budget; k8s-m5-prod-03, disruption
ORACLE-END
CASE-END
