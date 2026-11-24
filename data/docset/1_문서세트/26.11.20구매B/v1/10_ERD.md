# 다온정밀 구매·발주 시스템(협력사 포털) 구축 — ERD

| 항목 | 내용 |
|---|---|
| 프로젝트명 | 다온정밀 구매·발주 시스템(협력사 포털) 구축 |
| 발주처 | (가상) 다온정밀 |
| 수행사 | (가상) 누리정보기술 |
| 작성 팀 | 공통기술·연계&데이터(DA) |
| 문서 버전 | v1 |
| 문서 상태 | HEAD 승인본 |
| 공개 범위 | 프로젝트 내부 |
| 최초 작성일 | 2026-11-03 |
| 작성자 | 황보은 |
| 검토자 | 국하늘 |
| 승인자 | 어진혁 |

## 개정 이력

| 버전 | 일자 | 변경 내용 | 작성자 | 승인자 |
|---|---|---|---|---|
| v1 | 2026-11-03 | 최초 작성 | 황보은 | 어진혁 |

테이블정의서의 PK·FK·UK로 그린 논리 ERD. 테이블 18개, 관계 25개.

## 1. 다이어그램

```mermaid
erDiagram
  TB_SUPPLIER ||--o{ TB_SUPPLIER_USER : "SUP_ID"
  TB_SUPPLIER ||--o{ TB_ATTACH_FILE : "SUP_ID"
  TB_SUPPLIER_USER ||--o{ TB_LOGIN_HISTORY : "SUP_USER_ID"
  TB_MATERIAL ||--o{ TB_PR : "MATL_CD"
  TB_USER |o--o{ TB_PR : "BUYER_ID"
  TB_MATERIAL ||--o{ TB_RFQ : "MATL_CD"
  TB_USER ||--o{ TB_RFQ : "BUYER_ID"
  TB_RFQ ||--o{ TB_QUOTE : "RFQ_NO"
  TB_SUPPLIER ||--o{ TB_QUOTE : "SUP_ID"
  TB_SUPPLIER ||--o{ TB_PRICE_CONTRACT : "SUP_ID"
  TB_MATERIAL ||--o{ TB_PRICE_CONTRACT : "MATL_CD"
  TB_QUOTE |o--o{ TB_PRICE_CONTRACT : "QUOTE_ID"
  TB_SUPPLIER ||--o{ TB_PO : "SUP_ID"
  TB_USER ||--o{ TB_PO : "BUYER_ID"
  TB_PO ||--o{ TB_PO_ITEM : "PO_NO"
  TB_PR ||--o{ TB_PO_ITEM : "PR_NO"
  TB_MATERIAL ||--o{ TB_PO_ITEM : "MATL_CD"
  TB_PRICE_CONTRACT ||--o{ TB_PO_ITEM : "CNTR_ID"
  TB_PO ||--o{ TB_APPROVAL : "PO_NO"
  TB_PO ||--o{ TB_ASN : "PO_NO"
  TB_ASN |o--o{ TB_INSPECTION : "ASN_NO"
  TB_PO ||--o{ TB_INSPECTION : "PO_NO"
  TB_MATERIAL ||--o{ TB_INSPECTION : "MATL_CD"
  TB_USER |o--o{ TB_INSPECTION : "INSPECTOR_ID"
  TB_SUPPLIER ||--o{ TB_SUPPLIER_EVAL : "SUP_ID"
  TB_SUPPLIER {
    BIGINT SUP_ID PK
    CHAR BIZ_REG_NO UK
    VARCHAR ERP_VENDOR_CD UK
  }
  TB_SUPPLIER_USER {
    BIGINT SUP_USER_ID PK
    BIGINT SUP_ID FK
    VARCHAR LOGIN_ID UK
  }
  TB_ATTACH_FILE {
    BIGINT FILE_ID PK
    BIGINT SUP_ID FK
  }
  TB_LOGIN_HISTORY {
    BIGINT LOGIN_HIST_ID PK
    BIGINT SUP_USER_ID FK
  }
  TB_USER {
    VARCHAR USER_ID PK
  }
  TB_MATERIAL {
    VARCHAR MATL_CD PK
  }
  TB_PR {
    VARCHAR PR_NO PK
    INT PR_ITEM_NO PK
    VARCHAR MATL_CD FK
    VARCHAR BUYER_ID FK
  }
  TB_RFQ {
    VARCHAR RFQ_NO PK
    VARCHAR MATL_CD FK
    VARCHAR BUYER_ID FK
  }
  TB_QUOTE {
    BIGINT QUOTE_ID PK
    VARCHAR RFQ_NO FK
    BIGINT SUP_ID FK
  }
  TB_PRICE_CONTRACT {
    BIGINT CNTR_ID PK
    BIGINT SUP_ID FK
    VARCHAR MATL_CD FK
    BIGINT QUOTE_ID FK
  }
  TB_PO {
    VARCHAR PO_NO PK
    BIGINT SUP_ID FK
    VARCHAR BUYER_ID FK
  }
  TB_PO_ITEM {
    VARCHAR PO_NO PK_FK
    INT PO_ITEM_NO PK
    VARCHAR PR_NO FK
    VARCHAR MATL_CD FK
    BIGINT CNTR_ID FK
  }
  TB_APPROVAL {
    BIGINT APV_ID PK
    VARCHAR PO_NO FK
  }
  TB_ASN {
    VARCHAR ASN_NO PK
    VARCHAR PO_NO FK
  }
  TB_INSPECTION {
    VARCHAR INSP_NO PK
    VARCHAR ASN_NO FK
    VARCHAR PO_NO FK
    VARCHAR MATL_CD FK
    VARCHAR INSPECTOR_ID FK
  }
  TB_SUPPLIER_EVAL {
    BIGINT EVAL_ID PK
    BIGINT SUP_ID FK
  }
  TB_NOTICE {
    BIGINT NOTICE_ID PK
  }
  TB_IF_LOG {
    BIGINT IF_LOG_ID PK
  }
```

## 2. 관계 목록

| 부모 테이블 | 자식 테이블 | FK 컬럼 | 카디널리티 | 참조 |
|---|---|---|---|---|
| TB_SUPPLIER | TB_SUPPLIER_USER | SUP_ID | 1:N | 필수 |
| TB_SUPPLIER | TB_ATTACH_FILE | SUP_ID | 1:N | 필수 |
| TB_SUPPLIER_USER | TB_LOGIN_HISTORY | SUP_USER_ID | 1:N | 필수 |
| TB_MATERIAL | TB_PR | MATL_CD | 1:N | 필수 |
| TB_USER | TB_PR | BUYER_ID | 1:N | 선택 |
| TB_MATERIAL | TB_RFQ | MATL_CD | 1:N | 필수 |
| TB_USER | TB_RFQ | BUYER_ID | 1:N | 필수 |
| TB_RFQ | TB_QUOTE | RFQ_NO | 1:N | 필수 |
| TB_SUPPLIER | TB_QUOTE | SUP_ID | 1:N | 필수 |
| TB_SUPPLIER | TB_PRICE_CONTRACT | SUP_ID | 1:N | 필수 |
| TB_MATERIAL | TB_PRICE_CONTRACT | MATL_CD | 1:N | 필수 |
| TB_QUOTE | TB_PRICE_CONTRACT | QUOTE_ID | 1:N | 선택 |
| TB_SUPPLIER | TB_PO | SUP_ID | 1:N | 필수 |
| TB_USER | TB_PO | BUYER_ID | 1:N | 필수 |
| TB_PO | TB_PO_ITEM | PO_NO | 1:N | 필수 |
| TB_PR | TB_PO_ITEM | PR_NO | 1:N | 필수 |
| TB_MATERIAL | TB_PO_ITEM | MATL_CD | 1:N | 필수 |
| TB_PRICE_CONTRACT | TB_PO_ITEM | CNTR_ID | 1:N | 필수 |
| TB_PO | TB_APPROVAL | PO_NO | 1:N | 필수 |
| TB_PO | TB_ASN | PO_NO | 1:N | 필수 |
| TB_ASN | TB_INSPECTION | ASN_NO | 1:N | 선택 |
| TB_PO | TB_INSPECTION | PO_NO | 1:N | 필수 |
| TB_MATERIAL | TB_INSPECTION | MATL_CD | 1:N | 필수 |
| TB_USER | TB_INSPECTION | INSPECTOR_ID | 1:N | 선택 |
| TB_SUPPLIER | TB_SUPPLIER_EVAL | SUP_ID | 1:N | 필수 |
