import logging

import typer

from app.background_processes import fetcher

app = typer.Typer()


@app.command()
def fetcher_awards():
    fetcher.fetch_new_awards()


@app.command()
def fetch_new_awards_from_date(date: str):
    fetcher.fetch_new_awards_from_date(date)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    app()
