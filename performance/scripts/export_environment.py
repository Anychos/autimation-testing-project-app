import json

from inspect_environment import arguments, collect


def main():
    args = arguments(export=True)
    report = collect(args.prometheus_url, args.grafana_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
    print(args.output)


if __name__ == "__main__":
    main()
