import textwrap

def get_styles() -> str:
    return textwrap.dedent("""
    <style>
    /* Card Styles */
    .result-card {
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        background-color: #f8f9fa;
    }
    .result-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .rank-badge {
        background-color: #0d6efd;
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .card-title {
        font-size: 1.25em;
        font-weight: bold;
        margin-left: 8px;
    }
    /* Chip Styles */
    .chip-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 8px 0;
    }
    .chip {
        background-color: #e9ecef;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.85em;
        color: #495057;
    }
    .chip-hard {
        background-color: #cff4fc;
        color: #055160;
    }
    .chip-soft {
        background-color: #e2e3e5;
        color: #41464b;
    }
    .chip-unmatched {
        background-color: #f8d7da;
        color: #842029;
    }
    /* Banners and Badges */
    .alt-banner {
        background-color: #fff3cd;
        color: #664d03;
        padding: 8px 12px;
        border-radius: 4px;
        margin-bottom: 16px;
        font-weight: bold;
    }
    .template-badge {
        font-size: 0.75em;
        color: #6c757d;
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 2px 6px;
        margin-left: 8px;
        display: inline-block;
    }
    /* Clarify / No Match messages */
    .message-box {
        padding: 16px;
        background-color: #e7f1ff;
        color: #0c4128;
        border-left: 4px solid #0d6efd;
        border-radius: 4px;
        margin: 16px 0;
    }
    /* Narrow layout overrides */
    @media (max-width: 600px) {
        .result-card-header {
            flex-direction: column;
            align-items: flex-start;
        }
        .rank-badge {
            margin-bottom: 8px;
        }
    }
    </style>
    """)
