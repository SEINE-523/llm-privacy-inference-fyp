import argparse
import sys
from src.utils.initialization import (
    read_config_from_yaml,
    seed_everything,
    set_credentials,
    get_out_file,
)
from src.configs import Task


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config_path",
        type=str,
        default="configs/acs_config.yaml",
        help="Path to the config file",
    )
    args = parser.parse_args()

    cfg = read_config_from_yaml(args.config_path)
    seed_everything(cfg.seed)
    set_credentials(cfg)

    f, path = get_out_file(cfg)

    try:
        print(cfg)
        if cfg.task == Task.ACS:
            from src.acs.folk import run_acs

            run_acs(cfg)
        elif cfg.task == Task.PAN:
            from src.pan.pan import run_pan

            run_pan(cfg)
        elif cfg.task == Task.REDDIT:
            from src.reddit.reddit import run_reddit

            run_reddit(cfg)
        elif cfg.task == Task.CHAT:
            from src.chat.run_chat import run_chat

            run_chat(cfg)
        elif cfg.task == Task.CHAT_EVAL:
            from src.chat.eval_chat import run_eval_chat

            run_eval_chat(cfg)
        elif cfg.task == Task.SYNTHETIC:
            from src.synthetic.synthetic import run_synthetic

            run_synthetic(cfg)
        else:
            raise NotImplementedError(f"Task {cfg.task} not implemented")

    except ValueError as e:
        sys.stderr.write(f"Error: {e}")
    finally:
        if cfg.store:
            f.close()
