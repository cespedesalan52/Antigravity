"""
Configuración central de la aplicación.

Carga las variables de entorno desde un archivo .env y las expone
como un objeto de configuración tipado usando pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

# Valor "de relleno" de la clave secreta. Si la app arranca con esta clave,
# significa que no se configuró una propia (inseguro para producción).
SECRET_KEY_POR_DEFECTO = "CAMBIAR-ESTA-CLAVE-EN-PRODUCCION-conocimiento-abierto"


class Settings(BaseSettings):
    """
    Esquema de configuración de la aplicación.

    Las variables se leen automáticamente del archivo .env ubicado
    en la raíz del proyecto. Si no existe, se usan los valores por defecto.
    """

    # URL de conexión a PostgreSQL.
    # Formato: postgresql://usuario:password@host:puerto/nombre_db
    DATABASE_URL: str = "postgresql://usuario:password@localhost:5432/biblioteca_db"

    # Nombre del proyecto (aparece en la documentación de Swagger/ReDoc)
    PROJECT_NAME: str = "Conocimiento Abierto"

    # Entorno de ejecución: "development" o "production".
    # En "production" la app se niega a arrancar con configuración insegura.
    ENVIRONMENT: str = "development"

    # Orígenes permitidos para CORS (separados por coma). Como el frontend se
    # sirve desde la misma app, en producción suele alcanzar con el dominio
    # propio. Por defecto, solo orígenes de desarrollo local.
    ALLOWED_ORIGINS: str = (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:5500,http://127.0.0.1:5500"
    )

    # Clave secreta para firmar los tokens de acceso (HMAC-SHA256).
    # En producción DEBE definirse en el .env con un valor largo y aleatorio.
    SECRET_KEY: str = SECRET_KEY_POR_DEFECTO

    # Minutos de validez de un token de acceso antes de expirar.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas

    # Configuración de pydantic-settings:
    # - Lee las variables del archivo .env en la raíz del proyecto.
    # - env_file_encoding asegura la lectura correcta de caracteres especiales.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def origenes_permitidos(self) -> list[str]:
        """Lista de orígenes CORS a partir de la cadena separada por comas."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def es_produccion(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def secret_key_insegura(self) -> bool:
        """True si la clave secreta sigue siendo la de relleno."""
        return self.SECRET_KEY == SECRET_KEY_POR_DEFECTO


# Instancia global de configuración.
# Se importa en otros módulos como: from app.core.config import settings
settings = Settings()
