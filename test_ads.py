import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agent import root_agent
from google.genai import types as genai_types


async def main():
    """Testa o agente de Ads com um exemplo real."""
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="app", user_id="test_user", session_id="test_session"
    )
    runner = Runner(
        agent=root_agent, app_name="app", session_service=session_service
    )
    
    # Exemplo de briefing para anúncio Instagram
    query = """
landing_page_url: https://clinicasaude.com.br/consulta
objetivo_final: gerar agendamentos de consultas
perfil_cliente: mulheres de 25-45 anos preocupadas com saúde preventiva e bem-estar
"""
    
    print("🚀 Iniciando geração de anúncio Instagram...")
    print("=" * 50)
    
    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=query)]
        ),
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                print("\n📱 RESULTADO FINAL:")
                print("=" * 50)
                print(event.content.parts[0].text)
            else:
                print("Final event with no content or parts:")
                print(event)


if __name__ == "__main__":
    asyncio.run(main())