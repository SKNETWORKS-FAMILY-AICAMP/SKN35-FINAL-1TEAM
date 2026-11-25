// 실행 전: python export_casebook_for_docx.py
// NODE_PATH는 Codex 번들 node_modules가 포함돼야 합니다. README의 명령을 사용하세요.
const fs = require('fs');
const path = require('path');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel, PageBreak, ShadingType, BorderStyle, PageNumber, Header, Footer, PageOrientation } = require('docx');
const here = __dirname;
const records = JSON.parse(fs.readFileSync(path.join(here, 'casebook_docx_data.json'), 'utf8'));
const navy='17365D', pale='F3F7FA', green='E2F0D9', red='FCE4D6';
const border={style:BorderStyle.SINGLE,size:4,color:'B7C9D6'};
const val=(r,k)=>r[k]??'';
const run=(t,o={})=>new TextRun({text:String(t||''),font:'Arial',size:o.size||16,bold:o.bold,color:o.color,italics:o.italics});
const para=(t,o={})=>new Paragraph({children:[run(t,o)],spacing:{after:o.after??80,before:o.before??0},alignment:o.align});
function cell(t,w,o={}) { return new TableCell({width:{size:w,type:WidthType.DXA},shading:o.fill?{type:ShadingType.CLEAR,color:o.fill,fill:o.fill}:undefined,borders:{top:border,bottom:border,left:border,right:border},children:[new Paragraph({children:[run(t,{size:o.size||14,bold:o.bold,color:o.color})],spacing:{after:20}})]}); }
function table(headers,rows,widths) {
  const header=new TableRow({tableHeader:true,children:headers.map((h,i)=>cell(h,widths[i],{fill:navy,bold:true,color:'FFFFFF'}))});
  const body=rows.map(r=>new TableRow({children:r.map((v,i)=>cell(v,widths[i],{fill:i===0?pale:undefined}))}));
  return new Table({width:{size:9000,type:WidthType.DXA},columnWidths:widths,rows:[header,...body]});
}
const heading=(t,l=HeadingLevel.HEADING_1)=>new Paragraph({text:t,heading:l,spacing:{before:200,after:80}});
const short=(s,n)=>{s=String(s||'');return s.length>n?s.slice(0,n-1)+'…':s};
const count=(filter,j)=>records.filter(filter).filter(x=>val(x,'최종 판정')===j).length;
const groups=[['쇼핑몰 A · 가상 시나리오',x=>val(x,'시스템')==='쇼핑몰 A'&&val(x,'출처 유형')==='가상 시나리오'],['구매 B · 가상 시나리오',x=>val(x,'시스템')==='구매 B'&&val(x,'출처 유형')==='가상 시나리오'],['쇼핑몰 A · 실제 변경',x=>val(x,'시스템')==='쇼핑몰 A'&&val(x,'출처 유형')==='실제 변경'],['구매 B · 실제 변경',x=>val(x,'시스템')==='구매 B'&&val(x,'출처 유형')==='실제 변경']];
const yes=count(()=>true,'영향 있음'), no=count(()=>true,'영향 없음');
const content=[
 new Paragraph({children:[run('영향 팀 경계 사례집',{size:40,bold:true,color:navy})],alignment:AlignmentType.CENTER,spacing:{before:1800,after:180}}),
 new Paragraph({children:[run('초기 경계 후보 최종 재판정',{size:22,color:'52616B'})],alignment:AlignmentType.CENTER,spacing:{after:320}}),
 new Paragraph({children:[new PageBreak()]}), heading('1. 판정 결과'),
 table(['구분','영향 있음','영향 없음','합계'],[...groups.map(([n,f])=>[n,String(count(f,'영향 있음')),String(count(f,'영향 없음')),String(records.filter(f).length)]),['합계',String(yes),String(no),String(records.length)]],[3300,1600,1600,900]),
 heading('2. 판정 원칙'),
 para('대상 팀의 산출물·구현·인터페이스·테스트·수행계획에 실제 수정 또는 검증 작업이 생기면 영향 있음으로 판정한다.'),
 para('기존 TC 또는 화면이 없다는 사실만으로 비영향으로 보지 않는다. 반대로 이미 같은 값이 반영되었거나 별도 컴포넌트의 책임임이 확인되면 영향 없음으로 판정한다.'),
 heading('3. 사례별 최종 판정')
];
for(const [name,fn] of groups){
 content.push(heading(name,HeadingLevel.HEADING_2));
 const rows=records.filter(fn).map(x=>[val(x,'사례 ID'),val(x,'원본 ID'),val(x,'대상 팀'),val(x,'최종 판정'),val(x,'판정 원칙'),short(val(x,'변경 요약'),75),short(val(x,'최종 판정 근거'),115)]);
 content.push(table(['사례 ID','원본 ID','대상 팀','최종 판정','판정 원칙','변경 요약','최종 판정 근거'],rows,[900,750,1300,900,1200,1850,2100]));
}
const doc=new Document({styles:{default:{document:{run:{font:'Arial',size:18}}}},sections:[{properties:{page:{size:{width:16840,height:11907},orientation:PageOrientation.LANDSCAPE,margin:{top:700,right:700,bottom:650,left:700}}},headers:{default:new Header({children:[new Paragraph({children:[run('영향 팀 경계 사례집 | 최종 판정본',{size:14,color:'52616B'})],alignment:AlignmentType.RIGHT})]})},footers:{default:new Footer({children:[new Paragraph({children:[run('내부 검수용 | ',{size:14,color:'52616B'}),new TextRun({children:[PageNumber.CURRENT],size:14,color:'52616B'})],alignment:AlignmentType.CENTER})]})},children:content}]});
Packer.toBuffer(doc).then(buf=>fs.writeFileSync(path.join(here,'영향팀_경계사례집.docx'),buf));
