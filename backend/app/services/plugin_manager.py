from typing import Optional, Dict, Any, List
import importlib.util
import os
import logging

logger = logging.getLogger(__name__)


class PluginManager:
    def __init__(self):
        self._plugins: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Any]] = {
            "on_fixture_enrich": [],
            "on_fixture_create": [],
            "on_fixture_rank": [],
            "on_email_parse": [],
        }
    
    async def load_plugins(self):
        """Load all plugins from the plugins directory"""
        plugin_dir = os.path.join(os.path.dirname(__file__), "..", "plugins")
        
        for plugin_name in os.listdir(plugin_dir):
            plugin_path = os.path.join(plugin_dir, plugin_name)
            if os.path.isdir(plugin_path) and not plugin_name.startswith("_"):
                await self._load_plugin(plugin_name, plugin_path)
    
    async def _load_plugin(self, name: str, path: str):
        """Load a single plugin"""
        try:
            init_file = os.path.join(path, "__init__.py")
            if os.path.exists(init_file):
                module_name = f"app.plugins.{name}"
                spec = importlib.util.spec_from_file_location(module_name, init_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, "hooks"):
                        self._plugins[name] = module
                        self._register_hooks(name, module.hooks)
                        logger.info(f"Loaded plugin: {name}")
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
    
    def _register_hooks(self, name: str, hooks: Dict[str, Any]):
        """Register plugin hooks"""
        for hook_name, hook_func in hooks.items():
            if hook_name in self._hooks:
                self._hooks[hook_name].append(hook_func)
    
    async def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Execute all handlers for a hook"""
        results = []
        if hook_name in self._hooks:
            for handler in self._hooks[hook_name]:
                try:
                    result = await handler(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Hook {hook_name} error: {e}")
        return results
    
    def get_plugin_count(self) -> int:
        return len(self._plugins)
    
    def get_plugins(self) -> List[str]:
        return list(self._plugins.keys())
    
    def get_hooks(self) -> Dict[str, int]:
        return {hook: len(handlers) for hook, handlers in self._hooks.items()}


plugin_manager = PluginManager()
