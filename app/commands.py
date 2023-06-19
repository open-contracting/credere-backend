import logging

import typer

from app.background_processes import fetcher, remove_data_bg

app = typer.Typer()


@app.command()
def fetch_awards(email_invitation: str = None):
    fetcher.fetch_new_awards(email_invitation)


@app.command()
def fetch_new_awards_from_date(date: str, email_invitation: str = None):
    fetcher.fetch_new_awards_from_date(date, email_invitation)


@app.command()
def remove_data():
    remove_data_bg.remove_declined_rejected_accepted_data()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Output logs to the console
    )
    app()
