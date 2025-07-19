"""Audio compatibility layer for Python 3.13+"""

import sys
import warnings


def setup_audio_compatibility():
    """Setup audio compatibility for Python 3.13+ where audioop is removed."""
    if sys.version_info >= (3, 13):
        try:
            import audioop
        except ImportError:
            # Create a minimal mock for audioop if it doesn't exist
            # This is a workaround until pydub fully supports Python 3.13
            warnings.warn(
                "audioop module not found (removed in Python 3.13). "
                "Using compatibility mode. Some audio operations may be limited.",
                UserWarning
            )
            
            # Create a mock audioop module
            class MockAudioop:
                @staticmethod
                def mul(*args):
                    return args[0] if args else b''
                
                @staticmethod
                def tostereo(*args):
                    return args[0] if args else b''
                
                @staticmethod
                def add(*args):
                    return args[0] if args else b''
                
                @staticmethod
                def bias(*args):
                    return args[0] if args else b''
                
                @staticmethod
                def reverse(*args):
                    return args[0] if args else b''
                
                @staticmethod
                def lin2lin(*args):
                    return args[0] if args else b''
                
                @staticmethod
                def ratecv(*args):
                    return args[0] if args else b'', 0
                
                @staticmethod
                def max(*args):
                    return 0
                
                @staticmethod
                def avg(*args):
                    return 0
                
                @staticmethod
                def rms(*args):
                    return 0
                
                @staticmethod
                def findmax(*args):
                    return 0
                
                @staticmethod
                def findfit(*args):
                    return (0, 0)
                
                @staticmethod
                def findfactor(*args):
                    return 0
                
                @staticmethod
                def getsample(*args):
                    return 0
            
            # Inject the mock into sys.modules
            sys.modules['audioop'] = MockAudioop()
            sys.modules['pyaudioop'] = MockAudioop()


# Run setup when module is imported
setup_audio_compatibility()