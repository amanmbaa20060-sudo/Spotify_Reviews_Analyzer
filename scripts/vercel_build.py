"""CLI entry for Vercel build (keeps vercel.json buildCommand unchanged)."""

from spotify_app_review_analyzer.deploy.vercel_build import main

if __name__ == "__main__":
    main()
