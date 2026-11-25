# 영향팀 경계 사례집 파일 안내

| 파일 | 역할 |
|---|---|
| `영향팀_경계사례집_원본.xlsx` | **최종 판정의 원본 파일**. 189건의 초기 경계 근거, 최종 영향 있음·없음 판정, 판정 근거와 원칙을 수정·관리한다. |
| `영향팀_경계사례집.docx` | Excel의 최종 판정을 읽기 좋게 정리한 Word 사례집이다. |
| `영향팀_경계사례집.pdf` | DOCX를 PDF로 변환한 공유·열람용 파일이다. 내용 수정은 DOCX 또는 Excel에서 한다. |
| `export_casebook_for_docx.py` | Excel의 최종 판정 내용을 Word 생성용 데이터로 내보내는 스크립트다. |
| `casebook_docx_data.json` | Excel에서 내보낸 Word 생성용 중간 데이터다. 직접 수정하지 않는다. |
| `build_casebook_docx.js` | 중간 데이터를 사용해 DOCX 사례집을 다시 만드는 스크립트다. |
| `apply_feedback_revisions.py` | 1차 검토 의견(QA 원칙 축소, 판정 정정)을 마스터·구분 시트에 일괄 반영한 스크립트다. 이미 반영됨, 다시 실행하면 이후 수정한 근거를 덮어쓴다. |
| `refine_casebook_rationales.py` | 최종 판정 근거를 건별 문장(영향 있음: 고칠 산출물·조치, 영향 없음: 원래 경계 근거)으로 바꾼 스크립트다. 이미 반영됨. |
| `repair_excel.py` | Excel에서 복구 경고가 다시 발생할 때 표 메타데이터 없이 복구본을 만드는 스크립트다. |

## 수정 순서

1. `영향팀_경계사례집_원본.xlsx`에서 최종 판정·근거를 수정한다.
2. Word 사례집도 갱신해야 하면 `export_casebook_for_docx.py` 후 `build_casebook_docx.js`를 실행한다.
3. PDF가 필요하면 갱신된 DOCX를 PDF로 변환한다.
4. 판정을 바꾸면 `train_a.py`·`train_b.py`(가상 시나리오)와 `project_a.py`·`project_b.py`의 `IMPACT`(실제 변경)에도 같은 판정·근거를 반영하고 `build_docset.py`를 다시 실행한다. 라벨 엑셀은 py에서 생성되므로 엑셀 직접 수정은 덮어써진다.
