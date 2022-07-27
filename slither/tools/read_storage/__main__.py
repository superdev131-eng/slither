"""
Tool to read on-chain storage from EVM
"""
import json
import argparse
from os import environ

from crytic_compile import cryticparser

from slither import Slither
from slither.tools.read_storage.read_storage import SlitherReadStorage


def parse_args() -> argparse.Namespace:
    """Parse the underlying arguments for the program.
    Returns:
        The arguments for the program.
    """
    parser = argparse.ArgumentParser(
        description="Read a variable's value from storage for a deployed contract",
        usage=(
            "\nTo retrieve a single variable's value:\n"
            + "\tslither-read-storage $TARGET address --variable-name $NAME\n"
            + "To retrieve a contract's storage layout:\n"
            + "\tslither-read-storage $TARGET address --contract-name $NAME --layout\n"
            + "To retrieve a contract's storage layout and values:\n"
            + "\tslither-read-storage $TARGET address --contract-name $NAME --layout --values\n"
            + "TARGET can be a contract address or project directory"
        ),
    )

    parser.add_argument(
        "contract_source",
        help="The deployed contract address if verified on etherscan. Prepend project directory for unverified contracts.",
        nargs="+",
    )

    parser.add_argument(
        "--variable-name",
        help="The name of the variable whose value will be returned.",
        default=None,
    )

    parser.add_argument("--rpc-url", help="An endpoint for web3 requests.")

    parser.add_argument(
        "--key",
        help="The key/ index whose value will be returned from a mapping or array.",
        default=None,
    )

    parser.add_argument(
        "--deep-key",
        help="The key/ index whose value will be returned from a deep mapping or multidimensional array.",
        default=None,
    )

    parser.add_argument(
        "--struct-var",
        help="The name of the variable whose value will be returned from a struct.",
        default=None,
    )

    parser.add_argument(
        "--storage-address",
        help="The address of the storage contract (if a proxy pattern is used).",
        default=None,
    )

    parser.add_argument(
        "--contract-name",
        help="The name of the logic contract.",
        default=None,
    )

    parser.add_argument(
        "--layout",
        action="store_true",
        help="Toggle used to write a JSON file with the entire storage layout.",
    )

    parser.add_argument(
        "--value",
        action="store_true",
        help="Toggle used to include values in output.",
    )

    parser.add_argument(
        "--table-storage-layout",
        action="store_true",
        help="Print table view of storage layout",
    )

    parser.add_argument(
        "--table-storage-value",
        action="store_true",
        help="Print table view of storage layout & values",
    )

    parser.add_argument(
        "--silent",
        action="store_true",
        help="Silence log outputs",
    )

    parser.add_argument("--max-depth", help="Max depth to search in data structure.", default=20)

    cryticparser.init(parser)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if len(args.contract_source) == 2:
        # Source code is file.sol or project directory
        source_code, target = args.contract_source
        slither = Slither(source_code, **vars(args))
    else:
        # Source code is published and retrieved via etherscan
        target = args.contract_source[0]
        slither = Slither(target, **vars(args))

    if args.contract_name:
        contracts = slither.get_contract_from_name(args.contract_name)
    else:
        contracts = slither.contracts

    srs = SlitherReadStorage(contracts, args.max_depth)

    if args.rpc_url:
        # Remove target prefix e.g. rinkeby:0x0 -> 0x0.
        address = target[target.find(":") + 1 :]
        # Default to implementation address unless a storage address is given.
        if not args.storage_address:
            args.storage_address = address
        srs.storage_address = args.storage_address

        srs.rpc = args.rpc_url

    environ["SILENT"] = args.silent

    if args.table_storage_layout:
        environ["TABLE"] = "1"
        srs.get_all_storage_variables()
        srs.get_storage_layout()
        srs.print_table()
        return

    if args.table_storage_value:
        environ["TABLE"] = "1"
        srs.get_all_storage_variables()
        srs.get_storage_layout()
        srs.print_table_with_values()
        return

    if args.layout:
        srs.get_all_storage_variables()
        srs.get_storage_layout()
    else:
        assert args.variable_name
        # Use a lambda func to only return variables that have same name as target.
        # x is a tuple (`Contract`, `StateVariable`).
        srs.get_all_storage_variables(lambda x: bool(x[1].name == args.variable_name))
        srs.get_target_variables(**vars(args))

    # To retrieve slot values an rpc url is required.
    if args.value:
        assert args.rpc_url
        srs.get_slot_values()

    # Only write file if storage layout is used.
    if len(srs.slot_info) > 1:
        with open("storage_layout.json", "w", encoding="utf-8") as file:
            json.dump(srs.slot_info, file, indent=4)


if __name__ == "__main__":
    main()
