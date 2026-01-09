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
        "en": """1. **Upload Data**
    - Go to **Data Upload & Schema Builder**.
    - Upload your CSV file (must include header).
    - Review the "Data Preview" and "Data Profiling" sections to ensure correct loading.

2. **Configure Variables**
    - Check the "Variable Configuration" table.
    - Verify `mgm_type`: **g** (Gaussian/Continuous), **c** (Categorical), **p** (Poisson/Count).
    - *Tip*: Variables with few unique values (e.g., <5) are usually Categorical.

3. **Set Model Parameters**
    - **EBIC Gamma**: Controls sparsity. Default 0.5 is standard. Set to 0.25 for more edges, 0.75 for fewer.
    - **Rule Reg**: 'AND' is safer (fewer false positives). 'OR' is more sensitive.

4. **Run Analysis**
    - Click **Build & Validate model_spec.json**.
    - Expand "Pre-run Checklist" to ensure all green.
    - Click **🚀 Run MGM (EBIC)**.

5. **Visualize & Export**
    - View the interactive network graph.
    - Adjust "Edge Threshold" slider to filter weak edges.
    - Download `results.json` and `network.html` for your report.""",
        "vi": """1. **Tải dữ liệu**
    - Vào trang **Tải dữ liệu & Xây dựng Schema**.
    - Tải tệp CSV của bạn lên (phải có hàng tiêu đề).
    - Xem phần "Xem trước dữ liệu" và "Phân tích dữ liệu" để đảm bảo tải đúng.

2. **Cấu hình biến**
    - Kiểm tra bảng "Cấu hình biến".
    - Xác minh `mgm_type`: **g** (Gaussian/Liên tục), **c** (Phân loại), **p** (Poisson/Đếm).
    - *Mẹo*: Biến có ít giá trị duy nhất (ví dụ: <5) thường là Phân loại.

3. **Thiết lập tham số mô hình**
    - **EBIC Gamma**: Kiểm soát độ thưa. Mặc định 0.5 là chuẩn. Đặt 0.25 để có nhiều cạnh hơn, 0.75 để ít cạnh hơn.
    - **Rule Reg**: 'AND' an toàn hơn (ít dương tính giả). 'OR' nhạy hơn.

4. **Chạy phân tích**
    - Nhấp **Xây dựng & Xuất Đặc tả Mô hình**.
    - Mở rộng "Danh sách kiểm tra trước khi chạy" để đảm bảo tất cả đều xanh.
    - Nhấp **🚀 Chạy MGM (EBIC)**.

5. **Trực quan hóa & Xuất**
    - Xem biểu đồ mạng tương tác.
    - Điều chỉnh thanh trượt "Ngưỡng cạnh" để lọc các cạnh yếu.
    - Tải xuống `results.json` và `network.html` cho báo cáo của bạn.""",
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
    # Help text & Tooltips
    "help_ebic_gamma": {
        "en": "Tuning parameter for EBIC (0 to 1). Higher values (e.g., 0.5) penalize complexity more, resulting in sparser networks. Lower values (e.g., 0) allow more edges.",
        "vi": "Tham số điều chỉnh cho EBIC (0 đến 1). Giá trị cao (ví dụ: 0.5) phạt độ phức tạp nhiều hơn, dẫn đến mạng thưa hơn. Giá trị thấp (ví dụ: 0) cho phép nhiều cạnh hơn.",
    },
    "help_alpha": {
        "en": "Elastic net mixing parameter (0 to 1). 1 = Lasso (sparse), 0 = Ridge (dense), 0.5 = Elastic Net (balance).",
        "vi": "Tham số trộn Elastic net (0 đến 1). 1 = Lasso (thưa), 0 = Ridge (dày), 0.5 = Elastic Net (cân bằng).",
    },
    "help_rule_reg": {
        "en": "Rule to combine edge weights from two nodewise regressions. 'AND' requires both directions to be non-zero (conservative). 'OR' requires at least one.",
        "vi": "Quy tắc kết hợp trọng số cạnh từ hai hồi quy nút. 'AND' yêu cầu cả hai chiều đều khác không (thận trọng). 'OR' yêu cầu ít nhất một.",
    },
    "help_overparameterize": {
        "en": "If checked, estimates overparameterized model for categorical variables. Standard for MGM.",
        "vi": "Nếu chọn, ước lượng mô hình quá tham số cho biến phân loại. Chuẩn cho MGM.",
    },
    "help_scale_gaussian": {
        "en": "Standardize Gaussian variables to mean=0, std=1 before estimation. Recommended.",
        "vi": "Chuẩn hóa biến Gaussian về trung bình=0, độ lệch chuẩn=1 trước khi ước lượng. Khuyên dùng.",
    },
    "help_sign_info": {
        "en": "Attempt to recover edge sign (positive/negative relationship) from parameters.",
        "vi": "Cố gắng khôi phục dấu của cạnh (mối quan hệ tích cực/tiêu cực) từ tham số.",
    },
    "help_random_seed": {
        "en": "Set random seed for reproducibility of cross-validation (if used).",
        "vi": "Đặt seed ngẫu nhiên để tái tạo kết quả kiểm chứng chéo (nếu dùng).",
    },
    "help_aggregator": {
        "en": "Method to combine multiple parameters (e.g., for categorical variables) into a single edge weight scalar.",
        "vi": "Phương pháp kết hợp nhiều tham số (ví dụ: cho biến phân loại) thành một trọng số cạnh vô hướng.",
    },
    "help_sign_strategy": {
        "en": "How to assign a sign (+/-) to the aggregated edge weight. 'dominant' uses the sign of the parameter with largest magnitude.",
        "vi": "Cách gán dấu (+/-) cho trọng số cạnh đã tổng hợp. 'dominant' dùng dấu của tham số có độ lớn nhất.",
    },
    "help_zero_tol": {
        "en": "Parameters smaller than this threshold are treated as zero.",
        "vi": "Tham số nhỏ hơn ngưỡng này được coi là không.",
    },
    "help_edge_threshold": {
        "en": "Hide edges with absolute weight below this value in visualizations and tables.",
        "vi": "Ẩn các cạnh có trọng số tuyệt đối dưới giá trị này trong trực quan hóa và bảng.",
    },
    "help_layout": {
        "en": "Algorithm for positioning nodes in the graph visualization.",
        "vi": "Thuật toán định vị các nút trong trực quan hóa đồ thị.",
    },
    "help_centrality_compute": {
        "en": "Calculate Strength, Betweenness, and Closeness centrality metrics.",
        "vi": "Tính toán các chỉ số trung tâm: Độ mạnh, Trung gian, và Độ gần.",
    },
    "help_centrality_weighted": {
        "en": "Use edge weights in centrality calculations (vs treating all edges as 1).",
        "vi": "Sử dụng trọng số cạnh trong tính toán trung tâm (so với coi tất cả cạnh là 1).",
    },
    "help_centrality_abs": {
        "en": "Use absolute values of edge weights for centrality (avoids cancellation of pos/neg effects).",
        "vi": "Sử dụng giá trị tuyệt đối của trọng số cạnh cho tính trung tâm (tránh triệt tiêu tác động ranh/âm).",
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
