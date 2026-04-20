# 报销单填写 selector 采集清单

## 一、IAM 面板

### finance_share_entry
- text: 财务共享
- dom: `<div class="Item_LogoBox__3gozP"><div class="Item_cardTag__3h72s"></div><img class="Item_Logo__CzJ04" src="https://oss.paas.ifsg.com.cn/iam-iam-pub/photos/3abe2088-b534-49eb-9bef-17e6cfb1ca77.jpg"></div>`

## 二、财务共享首页

### menu_finance_share
- text: 财务共享
- dom: `<div id="_easyui_tree_13" class="tree-node"><span class="tree-hit tree-expanded"></span><span class="tree-icon tree-folder tree-folder-open"></span><span class="tree-title">财务共享</span></div>`

### menu_online_reimbursement
- text: 网上报账平台
- dom: `<div id="_easyui_tree_14" class="tree-node"><span class="tree-indent"></span><span class="tree-indent"></span><span class="tree-icon tree-file "></span><span class="tree-title">网上报账平台</span></div>`

### go_reimbursement_button
- text: 我要报账
- dom: `<div class="af-detail fg-color-standard" title="我要报账" oncontextmenu="return false;" id="FSBZ10020"><span class="af-defico"></span><img src="../ImageFunc/FSGFSBZ10020.png" style="vertical-align:middle;" height="40" width="40" onerror="javascript:this.onerror=null;this.src='../resources/DefaultBigImage.jpg'"><span class="funcName">我要报账</span></div>`

## 三、我要报账页

### new_bill_button
- text: 新建单据
- dom: `<div class="pros subpage"><h2>新建单据</h2></div>`

### bill_type_expense
- text: 费用报销类
- dom: `<a class="ti" href="#">费用报销类</a>`

### bill_subtype_business_entertainment
- text: 业务招待费报销
- dom: `<a id="7453727a-449f-4b2d-8a26-b3d99ba359fc" class="td" href="#">业务招待费报销</a>`

## 四、业务招待费报销页

### electronic_image_tab_entry
- text: 电子影像
- dom: `<span class="l-btn-left l-btn-icon-left"><span class="l-btn-text">电子影像</span><span class="l-btn-icon icon-SpeedLocation">&nbsp;</span></span>`

## 五、电子影像上传维护页

### local_upload_button
- text: 本地上传
- dom: `<span data-i18n-text="LOCAL_UPLOAD">本地上传</span>`

### upload_dialog
- text:
- dom: `<div id="UploadDialog">...</div>`

### choose_file_button
- text: 选择文件
- dom: `<div class="webuploader-pick">选择文件</div>`

### file_input
- text:
- dom: `none（Windows 文件选择控件）`

### start_upload_button
- text: 开始上传
- dom: `<div class="uploadBtn" data-i18n-text="START_UPLOADING">开始上传</div>`

### close_upload_dialog_button
- text:
- dom: `<a class="layui-layer-ico layui-layer-close layui-layer-close1" href="javascript:;"></a>`

## 六、发票识别区

### invoice_list_item
- text:
- dom: `<div class="sortwrap ui-sortable"><div id="15e24b8b320948f38ac151321d166279_box" class="box ui-sortable-handle">...</div></div>`

### recognize_button
- text: 识别
- dom: `<button id="btnInOCR" onclick="InoviceMgr.ocr();" class="ui-btn item-fp  item-cc item-qt" style="padding: 4px; display: inline-block;" type="button"><i class="fa fa-cloud"></i><span data-i18n-text="OCR">识别</span></button>`

### recognize_success_marker
- text: *发票号码
- dom: `<input type="text" data-bind="InvoiceNUM" disabled="disabled">`

### electronic_image_tab_close
- text:
- dom: `<li class="tabs-selected"><a href="javascript:void(0)" class="tabs-inner" style="height: 25px; line-height: 25px;"><span class="tabs-title tabs-closable">电子影像</span><span class="tabs-icon"></span></a><a href="javascript:void(0)" class="tabs-close"></a></li>`

## 七、报销单主页面与明细区

### attachment_count_input
- text: 附件个数*
- dom: `<span class="textbox numberbox" style="width: 100%; height: 26px;"><div class="fluidWrap" style="right: 0px;"><input type="text" class="textbox-text validatebox-text" autocomplete="off" placeholder="" style="margin-left: 0px; margin-right: 0px; padding-top: 5px; padding-bottom: 5px; width: 100%; padding-right: 3px; position: relative; left: -6px;"></div><input type="hidden" class="textbox-value" value="0"></span>`

### business_unit_input
- text: 业务单位
- dom: `<span class="combo" style="width: 100%; height: 26px; position: relative;"><div class="fluidWrap" style="right: 20px; position: absolute; left: 0px; display: block;"><input type="text" class="combo-text validatebox-text" autocomplete="off" placeholder="" style="width: 100%; height: 26px; line-height: 26px;" title=""></div><span class="adp-combobox" style="float: right; right: 0px; position: absolute;"><span style="height: 26px; display: none;" class="panel-tool-close combo-arrow"></span><span class="combo-arrow" style="height: 26px;"></span></span><input type="hidden" class="combo-value" value="01"></span>`

### payment_purpose_input
- text: 付款用途
- dom: `<div class="fluidWrap adp-textbox textbox-invalid" style="text-align:right;border: 1px solid #ababab;padding: 0px 3px;position:relative;height:20px;"><textarea class="easyui-validatebox input-text validatebox-text validatebox-invalid" style="height: 16px; width: 99.88% !important; border: 0px; padding: 2px 1px; line-height: normal;" id="XMultiTextBox2" fsm-type="textarea" fsm-visible="true" viewid="Form1" data-bindfield="a92f9cc8-1c21-41b3-9fc2-d2f1b8122089" data-options="required:true,tipPosition:'right',enableLocalStorage:false,validType:'length[0,120]'" data-clearfields="" data-bind="datasource:{dataSourceName:'DM_RO_BXDJ_CardInstance',value:'ROBXDJ.ROBXDJ_ZY'}" fsm-readonly="false" tipposition="right" maxlength="120" title=""></textarea></div>`

### detail_tab_select
- text: 报销明细信息
- dom: `<li class="tabs-selected"><a href="javascript:void(0)" class="tabs-inner" style="height: 27px; line-height: 27px;"><span class="tabs-title">报销明细信息</span><span class="tabs-icon"></span></a></li>`

### detail_row
- text:
- dom: `<tr id="datagrid-row-r2-2-0" datagrid-row-index="0" class="datagrid-row datagrid-row-editing datagrid-row-selected" style="">...</tr>`

### reception_type_select
- text: 接待类型
- dom: `<td field="ROBXMX_GXM2"><div style="white-space: normal; height: auto; width: 149px;" class="datagrid-cell datagrid-cell-c2-ROBXMX_GXM2 datagrid-editable"><table border="0" cellspacing="0" cellpadding="1"><tbody><tr><td><input type="text" class="datagrid-editable-input combobox-f combo-f textbox-f" style="display: none;"><span class="textbox combo" style="width: 147px; height: 26px;"><span class="textbox-addon textbox-addon-right adp-combobox" style="right: 0px;"><span style="display: none; height: 25px;" class="panel-tool-close combo-arrow"></span><a href="javascript:void(0)" class="textbox-icon combo-arrow" icon-index="0" tabindex="-1" style="width: 20px; height: 26px;"></a></span><input type="text" class="textbox-text validatebox-text" autocomplete="off" placeholder="" style="margin-left: 0px; margin-right: 20px; padding-top: 5px; padding-bottom: 5px; width: 122px;"><input type="hidden" class="textbox-value" name="" value="03"></span></td></tr></tbody></table></div></td>`

### company_count_input
- text: 公司人数
- dom: `<td field="ROBXMX_ZS2"><div style="white-space: normal; height: auto; width: 99px;" class="datagrid-cell datagrid-cell-c2-ROBXMX_ZS2 datagrid-editable"><table border="0" cellspacing="0" cellpadding="1"><tbody><tr><td><input type="text" class="datagrid-editable-input numberbox-f textbox-f" style="display: none;"><span class="textbox numberbox" style="width: 97px; height: 26px;"><input type="text" class="textbox-text validatebox-text" autocomplete="off" placeholder="" style="margin-left: 0px; margin-right: 0px; padding-top: 5px; padding-bottom: 5px; width: 89px;"><input type="hidden" class="textbox-value" value="0"></span></td></tr></tbody></table></div></td>`

### remark_input
- text: 备注
- dom: `<td field="ROBXMX_XXSM"><div style="white-space: normal; height: auto; width: 249px;" class="datagrid-cell datagrid-cell-c2-ROBXMX_XXSM datagrid-editable"><table border="0" cellspacing="0" cellpadding="1"><tbody><tr><td><input type="text" class="datagrid-editable-input validatebox-text" style="width: 239px; height: 22px;"></td></tr></tbody></table></div></td>`

## 八、保存结果

### save_button
- text: 保存
- dom: `<span class="l-btn-left l-btn-icon-left"><span class="l-btn-text">保存</span><span class="l-btn-icon icon-Save">&nbsp;</span></span>`
