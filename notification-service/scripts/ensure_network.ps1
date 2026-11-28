$existing = docker network ls --filter 'name=^taskflow-network$' --format '{{.Name}}'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($existing -ne 'taskflow-network') {
    docker network create taskflow-network
    if ($LASTEXITCODE -ne 0) {
        docker network inspect taskflow-network --format '{{.Name}}' | Out-Null
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}
