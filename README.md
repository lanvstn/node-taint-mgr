# node-taint-mgr

This is a small Kubernetes controller that manages taints on your nodes by label.

It allows you to define `wantedTaints` and `unwantedTaints`.

A possible use case is to remove the `kubernetes.azure.com/scalesetpriority` taint from spot nodes created by AKS.

Example:

```yaml
---
apiVersion: k8s.lanvstn.be/v1alpha1
kind: NodeTaintRule
metadata:
  name: test
spec:
  matchLabels:
    node.kubernetes.io/lifecycle: spot
  wantedTaints:
    - effect: NoSchedule
      key: randomtaint
      value: helloworld
  unwantedTaints:
    - effect: NoSchedule
      key: kubernetes.azure.com/scalesetpriority
      value: spot
```

## Running

```command
$ kopf run main.py --log-format plain
```

## Development status

Alpha software. Use at own risk.

## License

[MIT](LICENSE)
