# ruff: noqa: E501, W291
"""Internationalization (i18n) support for Hygeia-Graph."""

from typing import Any

# Language codes
LANGUAGES = {
    "en": "English",
    "vi": "Tiếng Việt",
}

# Translation dictionary
TRANSLATIONS: dict[str, dict[str, str]] = {
    # App title and description
    "app_title": {
        "en": "Hygeia-Graph",
        "vi": "Hygeia-Graph",
    },
    "app_description": {
        "en": "Mixed Graphical Models for Medical Network Analysis",
        "vi": "Mô hình Đồ thị Hỗn hợp cho Phân tích Mạng lưới Y tế",
    },
    # Navigation
    "nav_home": {
        "en": "Home",
        "vi": "Trang chủ",
    },
    "nav_data_upload": {
        "en": "Data Upload & Schema Builder",
        "vi": "Tải dữ liệu & Xây dựng Schema",
    },
    "nav_navigation": {
        "en": "Navigation",
        "vi": "Điều hướng",
    },
    "language": {
        "en": "Language",
        "vi": "Ngôn ngữ",
    },
    # Home page
    "home_about": {
        "en": "About",
        "vi": "Giới thiệu",
    },
    "home_description": {
        "en": """Hygeia-Graph is an interactive Streamlit application that enables researchers 
to build and visualize Mixed Graphical Model (MGM) networks from medical datasets. 
It supports mixed variable types (continuous, categorical, count), uses EBIC regularization 
for sparse network estimation, and provides interactive PyVis visualization with exportable 
artifacts for reproducible research.""",
        "vi": """Hygeia-Graph là một ứng dụng Streamlit tương tác giúp các nhà nghiên cứu 
xây dựng và trực quan hóa mạng lưới Mô hình Đồ thị Hỗn hợp (MGM) từ dữ liệu y tế. 
Ứng dụng hỗ trợ các loại biến hỗn hợp (liên tục, phân loại, đếm), sử dụng chính quy hóa EBIC 
để ước lượng mạng thưa, và cung cấp trực quan hóa tương tác PyVis với các artifacts 
có thể xuất để nghiên cứu có thể tái tạo.""",
    },
    "home_features": {
        "en": "Key Features",
        "vi": "Tính năng chính",
    },
    "feature_mixed_types": {
        "en": "**Mixed Variable Types**: Supports Gaussian (continuous), Categorical (nominal/ordinal), and Poisson (count) variables",
        "vi": "**Các loại biến hỗn hợp**: Hỗ trợ biến Gaussian (liên tục), Phân loại (danh nghĩa/thứ tự), và Poisson (đếm)",
    },
    "feature_ebic": {
        "en": "**EBIC Regularization**: Extended Bayesian Information Criterion for optimal sparsity tuning",
        "vi": "**Chính quy hóa EBIC**: Tiêu chí Thông tin Bayesian Mở rộng để điều chỉnh độ thưa tối ưu",
    },
    "feature_visualization": {
        "en": "**Interactive Visualization**: PyVis network graphs with customizable node/edge styling",
        "vi": "**Trực quan hóa tương tác**: Đồ thị mạng PyVis với kiểu dáng nút/cạnh tùy chỉnh",
    },
    "feature_centrality": {
        "en": "**Centrality Metrics**: Strength, betweenness, and closeness centrality computation",
        "vi": "**Chỉ số trung tâm**: Tính toán độ mạnh, trung gian, và độ gần trung tâm",
    },
    "feature_reproducible": {
        "en": "**Reproducible Artifacts**: Export `schema.json`, `model_spec.json`, `results.json` for full reproducibility",
        "vi": "**Artifacts có thể tái tạo**: Xuất `schema.json`, `model_spec.json`, `results.json` để tái tạo hoàn toàn",
    },
    "feature_validation": {
        "en": "**Contract Validation**: JSON Schema validation ensures artifact integrity",
        "vi": "**Xác thực hợp đồng**: Xác thực JSON Schema đảm bảo tính toàn vẹn của artifacts",
    },
    "home_quickstart": {
        "en": "Quick Start",
        "vi": "Bắt đầu nhanh",
    },
    "quickstart_steps": {
        "en": """1. **Upload Data**: Click on "Data Upload & Schema Builder" in the sidebar
2. **Review Variables**: Check auto-inferred variable types
3. **Configure Model**: Set EBIC parameters
4. **Run MGM**: Execute the Mixed Graphical Model
5. **Explore Results**: View network tables and visualization
6. **Export**: Download results.json, network.html, CSV files""",
        "vi": """1. **Tải dữ liệu**: Nhấp vào "Tải dữ liệu & Xây dựng Schema" ở thanh bên
2. **Xem xét biến**: Kiểm tra các loại biến được suy luận tự động
3. **Cấu hình mô hình**: Thiết lập tham số EBIC
4. **Chạy MGM**: Thực thi Mô hình Đồ thị Hỗn hợp
5. **Khám phá kết quả**: Xem bảng mạng và trực quan hóa
6. **Xuất**: Tải xuống results.json, network.html, các tệp CSV""",
    },
    "home_methods": {
        "en": "Methods",
        "vi": "Phương pháp",
    },
    "methods_description": {
        "en": """Hygeia-Graph implements **pairwise Mixed Graphical Models (k=2)** using the R `mgm` package.

| Setting | Default | Description |
|---------|---------|-------------|
| Lambda selection | EBIC | Extended Bayesian Information Criterion |
| EBIC gamma | 0.5 | Sparsity control (0–1) |
| Alpha | 0.5 | Elastic net mixing (0=Ridge, 1=Lasso) |
| Edge aggregator | max_abs | Map parameter blocks to scalar weights |
| Sign strategy | dominant | Assign edge sign from largest parameter |
| Missing policy | warn_and_abort | No internal imputation |

⚠️ **Note**: Hygeia-Graph does NOT impute missing values. If missing data is detected, analysis aborts with a warning.""",
        "vi": """Hygeia-Graph triển khai **Mô hình Đồ thị Hỗn hợp cặp đôi (k=2)** sử dụng gói R `mgm`.

| Cài đặt | Mặc định | Mô tả |
|---------|----------|-------|
| Chọn Lambda | EBIC | Tiêu chí Thông tin Bayesian Mở rộng |
| EBIC gamma | 0.5 | Kiểm soát độ thưa (0–1) |
| Alpha | 0.5 | Trộn elastic net (0=Ridge, 1=Lasso) |
| Bộ tổng hợp cạnh | max_abs | Ánh xạ khối tham số thành trọng số vô hướng |
| Chiến lược dấu | dominant | Gán dấu cạnh từ tham số lớn nhất |
| Chính sách missing | warn_and_abort | Không tự động điền giá trị thiếu |

⚠️ **Lưu ý**: Hygeia-Graph KHÔNG tự động điền giá trị thiếu. Nếu phát hiện dữ liệu thiếu, phân tích sẽ dừng với cảnh báo.""",
    },
    "home_disclaimer": {
        "en": "Disclaimer",
        "vi": "Tuyên bố miễn trừ",
    },
    "disclaimer_text": {
        "en": """⚠️ **Research Tool Only**: Hygeia-Graph is intended for exploratory network analysis. 
It is **not** a medical device and should **not** be used for clinical decision-making or diagnosis. 
Results should be interpreted by qualified researchers.""",
        "vi": """⚠️ **Chỉ dành cho Nghiên cứu**: Hygeia-Graph được thiết kế cho phân tích mạng khám phá. 
Đây **không** phải là thiết bị y tế và **không** nên được sử dụng để ra quyết định lâm sàng hoặc chẩn đoán. 
Kết quả nên được diễn giải bởi các nhà nghiên cứu có chuyên môn.""",
    },
    "contract_validation": {
        "en": "Contract Schema Validation",
        "vi": "Xác thực Schema Hợp đồng",
    },
    "contracts_found": {
        "en": "✅ All contract schemas found!",
        "vi": "✅ Tất cả schema hợp đồng đã được tìm thấy!",
    },
    "contracts_missing": {
        "en": "❌ Missing contract schemas!",
        "vi": "❌ Thiếu schema hợp đồng!",
    },
    "found_schemas": {
        "en": "Found schemas:",
        "vi": "Schema đã tìm thấy:",
    },
    "missing_schemas": {
        "en": "Missing:",
        "vi": "Thiếu:",
    },
    # Data page
    "upload_csv": {
        "en": "1. Upload CSV File",
        "vi": "1. Tải tệp CSV",
    },
    "choose_csv": {
        "en": "Choose a CSV file",
        "vi": "Chọn tệp CSV",
    },
    "loaded_rows_cols": {
        "en": "✅ Loaded {rows} rows and {cols} columns",
        "vi": "✅ Đã tải {rows} dòng và {cols} cột",
    },
    "data_preview": {
        "en": "📊 Data Preview",
        "vi": "📊 Xem trước dữ liệu",
    },
    "error_loading_csv": {
        "en": "❌ Error loading CSV: {error}",
        "vi": "❌ Lỗi tải CSV: {error}",
    },
    "upload_prompt": {
        "en": "👆 Please upload a CSV file to continue",
        "vi": "👆 Vui lòng tải lên tệp CSV để tiếp tục",
    },
    "data_profiling": {
        "en": "2. Data Profiling",
        "vi": "2. Phân tích dữ liệu",
    },
    "rows": {
        "en": "Rows",
        "vi": "Dòng",
    },
    "columns": {
        "en": "Columns",
        "vi": "Cột",
    },
    "missing_rate": {
        "en": "Missing Rate",
        "vi": "Tỷ lệ thiếu",
    },
    "variable_config": {
        "en": "3. Variable Configuration",
        "vi": "3. Cấu hình biến",
    },
    "variable_tip": {
        "en": "💡 Tip: Review the auto-inferred types below. You can edit mgm_type, measurement_level, level, and label as needed.",
        "vi": "💡 Mẹo: Xem xét các loại được suy luận tự động bên dưới. Bạn có thể chỉnh sửa mgm_type, measurement_level, level, và label theo nhu cầu.",
    },
    "generate_schema": {
        "en": "4. Generate & Export Schema",
        "vi": "4. Tạo & Xuất Schema",
    },
    "schema_preview": {
        "en": "📄 Schema Preview (JSON)",
        "vi": "📄 Xem trước Schema (JSON)",
    },
    "model_settings": {
        "en": "5. Model Settings (EBIC Regularization)",
        "vi": "5. Cài đặt mô hình (Chính quy hóa EBIC)",
    },
    "ebic_params": {
        "en": "⚙️ EBIC & Regularization Parameters",
        "vi": "⚙️ Tham số EBIC & Chính quy hóa",
    },
    "ebic_gamma": {
        "en": "EBIC Gamma",
        "vi": "EBIC Gamma",
    },
    "alpha_elastic": {
        "en": "Alpha (Elastic Net)",
        "vi": "Alpha (Elastic Net)",
    },
    "rule_reg": {
        "en": "Rule Regularization",
        "vi": "Quy tắc Chính quy hóa",
    },
    "random_seed": {
        "en": "Random Seed",
        "vi": "Seed ngẫu nhiên",
    },
    "edge_mapping": {
        "en": "🔗 Edge Mapping Configuration",
        "vi": "🔗 Cấu hình Ánh xạ Cạnh",
    },
    "aggregator": {
        "en": "Aggregator",
        "vi": "Bộ tổng hợp",
    },
    "sign_strategy": {
        "en": "Sign Strategy",
        "vi": "Chiến lược Dấu",
    },
    "zero_tolerance": {
        "en": "Zero Tolerance",
        "vi": "Ngưỡng Zero",
    },
    "viz_centrality": {
        "en": "📊 Visualization & Centrality (Optional)",
        "vi": "📊 Trực quan hóa & Trung tâm (Tùy chọn)",
    },
    "edge_threshold": {
        "en": "Edge Threshold",
        "vi": "Ngưỡng Cạnh",
    },
    "layout_algorithm": {
        "en": "Layout Algorithm",
        "vi": "Thuật toán Bố cục",
    },
    "build_model_spec": {
        "en": "6. Build & Export Model Specification",
        "vi": "6. Xây dựng & Xuất Đặc tả Mô hình",
    },
    "model_spec_preview": {
        "en": "📄 Model Spec Preview (JSON)",
        "vi": "📄 Xem trước Đặc tả Mô hình (JSON)",
    },
    "run_mgm": {
        "en": "7. Run MGM (R Backend)",
        "vi": "7. Chạy MGM (Backend R)",
    },
    "prerun_checklist": {
        "en": "✅ Pre-run Checklist",
        "vi": "✅ Danh sách kiểm tra trước khi chạy",
    },
    "data_loaded": {
        "en": "✅ Data loaded",
        "vi": "✅ Dữ liệu đã tải",
    },
    "schema_valid": {
        "en": "✅ schema.json valid",
        "vi": "✅ schema.json hợp lệ",
    },
    "model_spec_valid": {
        "en": "✅ model_spec.json valid",
        "vi": "✅ model_spec.json hợp lệ",
    },
    "missing_zero": {
        "en": "✅ Missing rate = 0%",
        "vi": "✅ Tỷ lệ thiếu = 0%",
    },
    "advanced_options": {
        "en": "⚙️ Advanced Options",
        "vi": "⚙️ Tùy chọn nâng cao",
    },
    "timeout_seconds": {
        "en": "Timeout (seconds)",
        "vi": "Thời gian chờ (giây)",
    },
    "run_mgm_btn": {
        "en": "🚀 Run MGM (EBIC)",
        "vi": "🚀 Chạy MGM (EBIC)",
    },
    "mgm_success": {
        "en": "✅ MGM completed successfully!",
        "vi": "✅ MGM hoàn thành thành công!",
    },
    "mgm_failed": {
        "en": "❌ MGM execution failed",
        "vi": "❌ Thực thi MGM thất bại",
    },
    "network_tables": {
        "en": "8. Network Tables & Centrality",
        "vi": "8. Bảng Mạng & Trung tâm",
    },
    "run_mgm_first": {
        "en": "⬆️ Run MGM first to see network tables",
        "vi": "⬆️ Chạy MGM trước để xem bảng mạng",
    },
    "interactive_network": {
        "en": "9. Interactive Network (PyVis)",
        "vi": "9. Mạng Tương tác (PyVis)",
    },
    "run_mgm_first_viz": {
        "en": "⬆️ Run MGM first to see network visualization",
        "vi": "⬆️ Chạy MGM trước để xem trực quan hóa mạng",
    },
}


def get_text(key: str, lang: str = "en", **kwargs: Any) -> str:
    """Get translated text for a given key.

    Args:
        key: Translation key
        lang: Language code ('en' or 'vi')
        **kwargs: Format arguments for the text

    Returns:
        Translated text, falls back to English if not found
    """
    if key not in TRANSLATIONS:
        return key

    text = TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get("en", key))

    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass

    return text


def t(key: str, lang: str = "en", **kwargs: Any) -> str:
    """Shorthand for get_text."""
    return get_text(key, lang, **kwargs)
