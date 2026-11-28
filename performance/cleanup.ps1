param(
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9][a-z0-9-]{0,39}$')][string] $DatasetId,
    [switch] $Full,
    [switch] $Apply,
    [string] $EnvFile
)
$ErrorActionPreference = 'Stop'
if (!$EnvFile) { $EnvFile = Join-Path $PSScriptRoot '.env.example' }
$Compose = @('compose', '--env-file', $EnvFile, '-p', 'taskflow-performance', '-f', "$PSScriptRoot/compose.yaml")
if ($Full) { $Compose += @('-f', "$PSScriptRoot/full.yaml", '--profile', 'full') }
$running = @(docker @Compose ps --status running --services)
if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect the Performance project' }
if ('backend' -notin $running) { throw 'Start the Performance backend' }
if ($Apply -and ('outbox-publisher' -in $running -or 'notification-worker' -in $running)) {
    throw 'Drain the queues, then stop the Performance outbox-publisher and every notification-worker'
}
$mode = if ($Apply) { '--apply' } else { '--dry-run' }
$Flags = @($mode)
if ($Apply -and $Full) {
    $queueJson = docker @Compose exec -T rabbitmq rabbitmqctl -q list_queues -p taskflow-performance name messages_ready messages_unacknowledged consumers --formatter=json
    if ($LASTEXITCODE -ne 0) { throw 'Unable to query Performance RabbitMQ' }
    $queues = $queueJson | ConvertFrom-Json
    if ('notification.events' -notin $queues.name) {
        throw 'Performance RabbitMQ topology could not be verified'
    }
    foreach ($queue in $queues) {
        if ($queue.messages_ready -ne 0 -or $queue.messages_unacknowledged -ne 0 -or $queue.consumers -ne 0) {
            throw 'Performance queues must be empty and have no consumers'
        }
    }
    $Flags += '--workers-stopped'
}
docker @Compose exec -T backend python /performance/scripts/cleanup_test_data.py --dataset-id $DatasetId @Flags
exit $LASTEXITCODE
