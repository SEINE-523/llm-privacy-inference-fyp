from src.configs import ModelConfig

from .model import BaseModel


def get_model(config: ModelConfig) -> BaseModel:
    if config.provider == "openai" or config.provider == "azure":
        from .open_ai import OpenAIGPT

        return OpenAIGPT(config)
    elif config.provider == "hf":
        from .hf_model import HFModel

        return HFModel(config)
    elif config.provider == "gcp":
        from .gcp.gcp_model import GCPPaLM

        return GCPPaLM(config)
    elif config.provider == "poe":
        from .poe.poe_model import PoeModel

        return PoeModel(config)
    elif config.provider == "loc":
        if config.name == "multi":
            from .multi_model import MultiModel

            models = []
            for sub_cfg in config.submodels:
                models.append(get_model(sub_cfg))

            return MultiModel(config, models)
        if config.name == "chain":
            from .chain_model import ChainModel

            models = []
            for sub_cfg in config.submodels:
                models.append(get_model(sub_cfg))

            return ChainModel(config, models)
        else:
            raise NotImplementedError

    else:
        raise NotImplementedError
