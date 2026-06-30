

class GlobalConfig:
    """Global store for configuration values"""


    _data_store: dict[str, any]

    @classmethod
    def load_dict(cls, model):
        """loads values from a configuration"""
        cls._data_store = model.model_dump()

    @classmethod
    def get(cls, key: str):
        """Gets a value from a configuration"""
        if key not in cls._data_store:
            return None
        return cls._data_store[key]

    @classmethod
    def set(cls, key: str, value: any):
        cls._data_store[key] = value

        

def config(config_key: str, kwarg_name: str):
    def decorator(fn):
        def inner(*args, **kwargs):
            kwargs[kwarg_name] = GlobalConfig.get(config_key)
            result = fn(*args, **kwargs)
            return result
        return inner
    return decorator


