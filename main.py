from __future__ import annotations

import json
import logging

import kopf
from kubernetes import client, config

MATCH_LABELS_KEY = "matchLabels"
WANTED_TAINTS_KEY = "wantedTaints"
UNWANTED_TAINTS_KEY = "unwantedTaints"
WANTS_TAINTS_KEY = "nodetaintmgr.k8s.lanvstn.be/wants-taints"

logging.basicConfig(level=logging.DEBUG)
config.load_kube_config()


def load_taint(taint: dict) -> str:
    """taints are handled as json strings because their dict form is unhashable"""
    return json.dumps(dict(sorted(taint.items())))


@kopf.index("nodetaintrules.k8s.lanvstn.be")
def rule_index(spec: dict, **_):
    return {
        (label_k, label_v): {
            WANTED_TAINTS_KEY: spec.get(WANTED_TAINTS_KEY, []),
            UNWANTED_TAINTS_KEY: spec.get(UNWANTED_TAINTS_KEY, []),
        }
        for label_k, label_v in spec.get(MATCH_LABELS_KEY, {"": ""}).items()
    }


@kopf.on.resume("node")
@kopf.on.create("node")
@kopf.on.field("node", field="spec.taints")
@kopf.on.field("node", field=("metadata", "annotations", WANTS_TAINTS_KEY))  # tuple field format because of dots in key
def handle_node(name: str, spec: dict, labels: dict, rule_index: kopf.Index, **_):
    old_state = set([load_taint(taint) for taint in spec.get("taints", [])])
    desired_state = old_state.copy()

    matching_rules = [
        rule_resources for label, rule_resources in rule_index.items() if label in labels.items() or label == ("", "")
    ]

    for rule_resources in matching_rules:
        for rule in rule_resources:
            desired_state |= set([load_taint(taint) for taint in rule.get(WANTED_TAINTS_KEY, [])])
            desired_state -= set([load_taint(taint) for taint in rule.get(UNWANTED_TAINTS_KEY, [])])

    if old_state != desired_state:
        logging.info(f"updating taints for node: {name}")
        logging.info(f"new taints: {desired_state}")
        v1 = client.CoreV1Api()
        v1.patch_node(name, {"spec": {"taints": [json.loads(taint) for taint in desired_state]}})


@kopf.on.event("nodetaintrules.k8s.lanvstn.be")
def handle_rule(name, namespace, spec, **_):
    logging.info(f"handling nodetaintule {namespace}/{name} {spec}")

    # Trick to force reconcile by changing an annotation field which we watch
    # TODO: trigger handle_node without having to resort to this
    v1 = client.CoreV1Api()
    nodes = v1.list_node().items

    node: client.V1Node
    for node in nodes:
        v1.patch_node(
            node.metadata.name,
            {
                "metadata": {
                    "annotations": {WANTS_TAINTS_KEY: str(int(node.metadata.annotations.get(WANTS_TAINTS_KEY, 0)) + 1)}
                }
            },
        )
