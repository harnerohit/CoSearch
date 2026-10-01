import textwrap

def get_styles() -> str:
    return textwrap.dedent("""
    <style>
    /* Card Styles */
    .result-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .result-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }
    .result-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        flex-wrap: wrap;
        gap: 8px;
    }
    .rank-badge {
        background-color: #0d6efd;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .card-title {
        font-size: 1.35em;
        font-weight: 700;
        margin-left: 10px;
        color: #212529;
    }
    .price-block {
        font-size: 1.3em;
        color: #198754;
        font-weight: 700;
    }
    .price-unit {
        font-size: 0.7em;
        color: #6c757d;
        font-weight: normal;
    }
    
    /* Chip Styles */
    .chip-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 12px 0;
    }
    .chip {
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.85em;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
    }
    .chip-amenity {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        color: #495057;
    }
    .chip-hard {
        background-color: #e0f3ff;
        border: 1px solid #b8daff;
        color: #004085;
    }
    .chip-soft {
        background-color: #f8f9fa;
        border: 1px solid #e2e3e5;
        color: #41464b;
    }
    .chip-unmatched {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    
    /* Metadata Row */
    .metadata-row {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        font-size: 0.95em;
        color: #495057;
        margin-top: 8px;
    }
    
    /* Banners and Badges */
    .template-badge {
        font-size: 0.75em;
        color: #6c757d;
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 2px 6px;
        margin-left: 8px;
        vertical-align: middle;
    }
    
    /* Message Boxes */
    .msg-box {
        padding: 16px 20px;
        border-radius: 8px;
        margin: 16px 0;
        font-weight: 500;
    }
    .msg-info {
        background-color: #cff4fc;
        color: #055160;
        border-left: 4px solid #0dcaf0;
    }
    .msg-warning {
        background-color: #fff3cd;
        color: #664d03;
        border-left: 4px solid #ffc107;
    }
    .msg-error {
        background-color: #f8d7da;
        color: #842029;
        border-left: 4px solid #dc3545;
    }
    
    /* Clarify query box */
    .parsed-query-box {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 20px;
    }

    /* Narrow layout overrides */
    @media (max-width: 600px) {
        .result-card-header {
            flex-direction: column;
            align-items: flex-start;
        }
        .price-block {
            margin-top: 8px;
        }
    }
    </style>
    """)
