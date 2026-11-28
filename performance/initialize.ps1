$ErrorActionPreference = 'Stop'
$network = docker network ls --filter 'name=^taskflow-performance-observe$' --quiet
if ($LASTEXITCODE -ne 0) { throw 'Failed to list Docker networks' }
if ($network) {
    $details = docker network inspect $network | ConvertFrom-Json
    if ($details.Labels.'taskflow.scope' -ne 'performance') {
        throw 'Unexpected Docker network with the performance network name'
    }
} else {
    docker network create --label taskflow.scope=performance taskflow-performance-observe
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create the performance network' }
}
