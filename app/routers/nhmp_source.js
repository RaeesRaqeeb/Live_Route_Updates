<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <script src="../js/jquery.js"></script>
    <script>
        $(document).ready(function () {
        $('#englishDiv').load('english.html');
        $('#urduDiv').load('urdu.html');
    });


        function blink(selector) {
        $(selector).fadeOut('slow', function () {
            $(this).fadeIn('slow', function () {
                blink(this);
            });
        });
    }

        blink('.englishDiv');
        blink('.urduDiv');


    </script>
    <style>
        .red {
        background - color: red;
    }

        .yellow {
        background - color: yellow;
    }
    </style>


    <meta charset="utf-8"/>
    <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <meta name="description" content=""/>
    <meta name="author" content=""/>

    <title>NHMP - Travel Advisory</title>

    <!-- Bootstrap Core CSS -->
    <link href="../css/bootstrap.min.css" rel="stylesheet"/>


    <!-- Custom CSS -->
    <link href="../css/sb-admin.css" rel="stylesheet"/>

    <!-- Morris Charts CSS -->
    <link href="../css/plugins/morris.css" rel="stylesheet"/>

    <!-- Custom Fonts -->
    <link href="../font-awesome/css/font-awesome.min.css" rel="stylesheet" type="text/css"/>

    <!-- HTML5 Shim and Respond.js IE8 support of HTML5 elements and media queries -->
    <!-- WARNING: Respond.js doesn't work if you view the page via file:// -->
    <!--[if lt IE 9]>
        <script src="https://oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
        <script src="https://oss.maxcdn.com/libs/respond.js/1.4.2/respond.min.js"></script>
    <![endif]-->


    <style type="text/css">
        .auto-style1 {
        font - weight: bold;
    }
        .auto-style4 {
        height: auto;
    }
    </style>


</head>
<body>


<div class="col-lg-12">
    <div class="panel panel-primary">
        <div class="panel-heading">
            <h3 class="panel-title"><i class="fa fa-bar-chart-o"></i>NHMP Travel Advisory: </h3>
        </div>
        <div class="panel-body">

            <div class="form-group col-lg-16">
                <form method="post" action="./ViewTravel.aspx" id="ctl00">
                    <div class="aspNetHidden">
                        <input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE"
                               value="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b3JrZGQCAg9kFgJmDw8WAh8DBWlEaXZlcnNpb24gOiBUcmFmZmljIG9mIHRoZSBOb3J0aCBTaWRlIGRpdmVydGVkIGZyb20gbmVhciBtb3JvIHRvbGwgcGxhemEgKEtNIDMyMSB0byAzMjYpIGR1ZSB0byBSb2FkIFdvcmtkZAIDD2QWAmYPDxYCHwMFckRpdmVyc2lvbiA6IFRyYWZmaWMgb2YgdGhlIE5vcnRoIFNpZGUgZGl2ZXJ0ZWQgZnJvbSB0diBib29zdGVyIHRvIG5vb3JwdXIgdmlsbGFnZSAoS00gMzMxIHRvIDMzMikgZHVlIHRvIFJvYWQgV29ya2RkAgQPZBYCZg8PFgIfAwVtRGl2ZXJzaW9uIDogVHJhZmZpYyBvZiB0aGUgTm9ydGggU2lkZSBkaXZlcnRlZCBmcm9tIHRhc3NpIHB1bXAgdG8gbmFuZ28gc2hhaCAoS00gMzMzIHRvIDMzNSkgZHVlIHRvIFJvYWQgV29ya2RkAgUPZBYCZg8PFgIfAwVyRGl2ZXJzaW9uIDogVHJhZmZpYyBvZiB0aGUgTm9ydGggU2lkZSBkaXZlcnRlZCBmcm9tIGt1bmRhIGtoYWhpIHRvIGJoaXJpeWEgYnlwYXNzIChLTSAzNDcgdG8gMzUyKSBkdWUgdG8gUm9hZCBXb3JrZGQCBg9kFgJmDw8WAh8DBXZEaXZlcnNpb24gOiBUcmFmZmljIG9mIHRoZSBOb3J0aCBTaWRlIGRpdmVydGVkIGZyb20gc2hhaCBqYW1hbCB0byBrYW5kaWFybyB0b2xsIHBsYXphIChLTSAzNjQgdG8gMzcwKSBkdWUgdG8gUm9hZCBXb3JrZGQCBw9kFgJmDw8WAh8DBWtEaXZlcnNpb24gOiBUcmFmZmljIG9mIHRoZSBOb3J0aCBTaWRlIGRpdmVydGVkIGZyb20gc2FsYWggcmFqcGVyIHRvIGhhbGFuaSAoS00gMzc1IHRvIDM4MCkgZHVlIHRvIFJvYWQgV29ya2RkAggPZBYCZg8PFgIfAwUvRm9nIGZyb20gIChLTSApIHRvICAoS00gKS4gVmlzaWJpbGl0eSA9ICBtZXRlcnNkZAIJDw8WAh8EaGRkAn8PDxYCHwMFK0xhc3QgdXBkYXRlZCBvbiA6IDxiPjMwLUp1bC0yNiAxMjo0OTozMDwv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"/>
                    </div>

                    <script type="text/javascript">
                        //
                        <
                        ![CDATA[
                        var theForm = document.forms['ctl00'];
                        if (!theForm) {
                        theForm = document.ctl00;
                    }
                        function __doPostBack(eventTarget, eventArgument
                    ) {
                        if (!theForm.onsubmit || (theForm.onsubmit() != false)) {
                        theForm.__EVENTTARGET.value = eventTarget;
                        theForm.__EVENTARGUMENT.value = eventArgument;
                        theForm.submit();
                    }
                    }
                        //]]>
                    </script>


                    <script
                        src="/WebResource.axd?d=PJcG0RDD4whVllS9BUFeypCOYp5ZzrLmuiE-BZ-u3TEwHhadAIhFTNzKp7R4lf2pANwJCI0JE345SrXevdWD0viRX66JQv_8CdmLJBb8E0c1&amp;t=638901716248157332"
                        type="text/javascript"></script>

                    <div class="aspNetHidden">

                        <input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="0090AEE3"/>
                        <input type="hidden" name="__SCROLLPOSITIONX" id="__SCROLLPOSITIONX" value="0"/>
                        <input type="hidden" name="__SCROLLPOSITIONY" id="__SCROLLPOSITIONY" value="0"/>
                        <input type="hidden" name="__EVENTTARGET" id="__EVENTTARGET" value=""/>
                        <input type="hidden" name="__EVENTARGUMENT" id="__EVENTARGUMENT" value=""/>
                    </div>


                    <table style="width:60%; text-align:center">
                        <tr>
                            <td style="width:10%"><strong>Legends</strong>:</td>
                            <td style="width:30%" class="yellow">Public Protest</td>
                            <td style="width:30%" class="alert-success">Road & Weather Clear</td>
                            <td style="width:30%" class="alert-warning">Other Information</td>

                        </tr>
                    </table>
                    <br/>

                    <span id="Label1" style="font-size:8pt;"></span>


                    <table CssClass="table" border="1" width="100%"
                           style="font-family: Arial, Helvetica, sans-serif; font-size: small;">

                        <tr>
                            <td rowspan="5" style="width: 15%"><strong>Motorway North Zone</strong><br/>
                                Ph:051-9278808
                            </td>
                            <td width="15%"><strong>Sector M1</strong>
                                <br/>
                                (Peshawar to Islambad Motorway)<br/>
                                Ph: 093-8490463<br/>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 0331-5999130<br/>
                            </td>
                            <td>
                                <div>
                                    <table class="Table" cellspacing="0" id="GridView1"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblM1"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 11:26:58</b></span>

                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>E35<br/>
                            </strong>(Burhan to Thakot)<strong><br/>
                            </strong>Ph: 0992-402281
                            </td>
                            <td>

                                <div>
                                    <table class="Table" cellspacing="0" id="GridView23"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Road Closed: from maira ali khan (KM 37) to Maira ali khan (KM .7) due
                                                to Road Work (Road Side : North Bound 1st Lane )
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from Akhhoon Di Bandi (KM 49) to Akhhoon Di Bandi (KM 49)
                                                due to Road Work (Road Side : North Bound 2nd Lane 3rd Lane )
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from Banda dour (KM 55) to Banda dour (KM 55) due to Road
                                                Work (Road Side : South Bound 1st Lane )
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from maira ali khan (KM 37) to maira ali khan (KM 37) due
                                                to Road Work (Road Side : North Bound 3rd Lane )
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lble35"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 12:54:04</b></span>
                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector M2North</strong><br/>
                                (Islambad to Kot Momin Motorway)<br/>
                                Ph:051-4675190<br/>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 051-4675291
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView7"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Road Closed: from Balkasar (KM 265) to Balkasar (KM 265) due to Road
                                                Work (Road Side : North Bound 1st Lane )
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from Kallar Khar (KM 244) to kalar kahar (KM 244) due to
                                                Road Work (Road Side : North Bound 1st Lane )
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from salt range (KM 230) to salt range (KM 230) due to Road
                                                Work (Road Side : South Bound 1st Lane )
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from Chakri (KM 312) to Chakri (KM 312) due to Road Work
                                                (Road Side : North Bound 1st Lane 2nd Lane )
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from Capital Smart City (KM 330) to Capital Smart City (KM
                                                330) due to Road Work (Road Side : North Bound 2nd Lane 3rd Lane )
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from Lillah (KM 217) to Lillah (KM 217) due to Road Work
                                                (Road Side : North Bound 1st Lane 2nd Lane )
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from Chakri (KM 307) to Chakri (KM 307) due to Road Work
                                                (Road Side : North Bound 2nd Lane 3rd Lane )
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from Chakri (KM 317) to Chakri (KM 317) due to Road Work
                                                (Road Side : South Bound 1st Lane 2nd Lane )
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblM2N"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 14:29:39</b></span>


                            </td>
                        </tr>


                        <tr>
                            <td width="15%"><strong>Sector M</strong>1<span class="auto-style1">4</span><br/>
                                (Hakla to D.I.Khan)<br/>
                                Ph:045-9395055
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView25"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Road Closed: from Baghi Qamar (KM 239) to Baghi Qamar (KM 239) due to
                                                Road Work (Road Side : North Bound 1st Lane )
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblM14" style="font-size:8pt;"></span>


                            </td>
                        </tr>


                        <tr>
                            <td width="15%"><strong>Sector Swat Expressway </strong><br/>
                                (Col Sher khan to Chakdara)<br/>
                                Ph:0346-9074406
                            </td>
                            <td>


                                <div>
                                    <table class="table" cellspacing="0" id="GridView29"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblSEW29"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 07:54:49</b></span>

                            </td>
                        </tr>


                        <tr>
                            <td rowspan="3" style="width: 15%"><strong>Motorway Central-I<br/>
                            </strong>Ph:042-99333319<br/>
                            </td>
                            <td width="15%" class="auto-style4"><strong>Sector M2-South</strong><br/>
                                (Kot Momin to Lahore )<br/>
                                Ph:<span
                                    style="color: rgb(34, 34, 34); font-family: Arial, Helvetica, sans-serif; font-size: small; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: start; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;"> 048-6886112<br/>
                                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 0332-0521734</span></td>
                            <td class="auto-style4">
                                <div>
                                    <table class="table" cellspacing="0" id="GridView8"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Weather : Cloudy from Thokar Niaz Baig (KM 00) to Kotmomin (KM 162).
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblM2S"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 12:59:28</b></span>

                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector M3</strong><br/>
                                (Lahore to Abdul Hakeem)<br/>
                                &nbsp;Ph:0311-4881145 <br/>
                            </td>
                            <td>
                                <div>
                                    <table class="Table" cellspacing="0" id="GridView18"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Weather : Cloudy from faizpur (KM 1147) to darkhana (KM 918).</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblM3"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 07:54:14</b></span>

                            </td>
                        </tr>


                        <tr>
                            <td width="15%"><strong>Sector </strong>M<span class="auto-style1">11</span><br/>
                                (00 Mehmood Booti to 91 Sambrial Toll Plaza Sialkot)<br/>
                                Ph: 052-6300185 <br/>
                            </td>
                            <td>
                                <div>
                                    <table class="Table" cellspacing="0" id="GridView24"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblM11"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 13:00:06</b></span>

                            </td>
                        </tr>


                        <tr>
                            <td rowspan="4" style="width: 15%"><strong>Motorway Central-II Zone<br/>
                            </strong>Ph: 061-9330971<strong><br/>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                            </strong>061-4482307<strong><br/>
                            </strong><br/>
                            </td>
                            <td width="15%"><strong>Sector M4 </strong><br/>
                                (Pindibhatiya-KM290 to Abdul Hakeem-KM89)<br/>
                                Ph: 046-2526025
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView19"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblM41"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 09:20:43</b></span>


                            </td>
                        </tr>


                        <tr>
                            <td width="15%"><strong>Sub-Sector M4 </strong><br/>
                                (Abdul Hakeem KM89 to Sher Shah KM00 )<br/>
                                Ph:0318-7731203
                            </td>
                            <td>


                                <div>
                                    <table class="table" cellspacing="0" id="GridView27"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblSubSecM4"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 14:01:49</b></span>

                            </td>
                        </tr>


                        <tr>
                            <td width="15%"><strong>
                                <br/>
                                Sector-1 M5</strong><br/>
                                (Sher Shah Multan-KM772 to Zahier Pir-KM579)<br/>
                                Ph:0301-9316623<br/>
                            </td>
                            <td>
                                <div>
                                    <table class="Table" cellspacing="0" id="GridView13"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblM51"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 14:23:32</b></span>

                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector-2 M5 </strong><br/>
                                (Zahir
                                Pir KM579 to Rohri Toll Plaza KM386)<br/>
                                Ph: 0315-4482532<br/>
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView20"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblM52"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 07:54:35</b></span>


                            </td>
                        </tr>


                        <tr>
                            <td rowspan="4" style="width: 15%"><strong>N-5 North Zone<br/>
                            </strong>(Highway N-5 Peshawar to Lahore &amp; IMDC)<br/>
                                Ph: 051-9278814
                            </td>
                            <td width="15%"><strong>Sector North-I</strong>
                                <br/>
                                (GT Road Peshawar to Islambad)<br/>
                                Ph:0923-695033
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView9"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblN1"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 07:52:14</b></span>

                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector North-II</strong><br/>
                                (Islambad to Kharian)<br/>
                                Ph:0544-226055<br/>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 0544-226056
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView10"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Weather : Partial Cloudy from Kharian Cantt (KM 1410) to Sawan (KM
                                                1533).
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Road Closed: from sher baz hotel (KM 1465) to sher baz hotel (KM 1465)
                                                due to Road Work (Road Side : South Bound 1st Lane )
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblN2"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 14:44:51</b></span>

                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector North-III</strong>
                                <br/>
                                (Kharian to Lahore )<br/>
                                Ph:055-6816200<br/>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 055-6813500
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView11"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblN3"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 12:51:26</b></span>

                            </td>
                        </tr>


                        <tr>
                            <td width="15%"><strong>Sector </strong><span class="auto-style1">IMDC</span><br/>
                                (Islamabad to Murree N-75)<br/>
                                Ph:0304-9256202
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView16"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from 43 (KM 45 Masyari)
                                                due to Road Damage
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Weather : Cloudy from 17 mile (KM 13 ) to Lowertopa (KM 54).</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblIMDC"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 07:53:46</b></span>

                            </td>
                        </tr>

                        <tr>
                            <td rowspan="3" style="width: 15%"><strong>N-5 Central Zone<br/>
                            </strong>(Highway N-5 Lahore to Sadiqabad)<br/>
                                Ph:042-99332852, 0310-4673937
                            </td>
                            <td width="15%"><strong>Sector Central-I</strong>
                                <br/>
                                (Lahore to Chichawatni)<br/>
                                Ph:044-2700669, 044-2700668
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView2"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Weather : Cloudy from jinaah terminal (KM 1245) to sanpal chowk (KM
                                                1045).
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Weather : Rain from Dina nath (KM 1212) to Shaheen CNG (KM 1169).</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblC1"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 15:01:35</b></span>

                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector Central-II</strong><br/>
                                (Mian Chanu to Bahawalpur)<br/>
                                Ph:0303-0984130, 061-6779130
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView3"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblC2"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 13:36:11</b></span>

                                i
                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector Central-III</strong>
                                <br/>
                                (Ahmed Pur East to Sadiqabad)<br/>
                                Ph:0324-5810744, 068-5678008, 068-5678010
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView4"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblC3"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 14:48:53</b></span>

                            </td>
                        </tr>


                        <tr>
                            <td rowspan="5" style="width: 15%"><strong>N-5 South Zone<br/>
                            </strong>(Rahim Yar Khan to Karachi)<br/>
                                Ph:021-99333334-35
                            </td>
                            <td width="15%"><strong>Sector South-I</strong>
                                <br/>
                                (Kot Sabzal to Halani)<br/>
                                Ph:071-9310878
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView5"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the South Side diverted from 400 to 408 SB
                                                (Hingorja city to Shah G Machine) (KM 7km is set up and south bound
                                                traffic is diverted onto the northbound carriageway) due to Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the South Side diverted from 390 to 399 SB (Kotri
                                                kabir to Hingorja city) (KM 9km is set up and south bound traffic is
                                                diverted onto the northbound carriageway.) due to Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from 383 to 390 NB Halani
                                                to Kotri kabir (KM 7km is set up and northbound traffic is diverted onto
                                                the Southbound carriageway.) due to Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the South Side diverted from 599 Punal Mazari PSO
                                                Pump SB (KM 599 SB on Second lane traffic moving on first lane) due to
                                                Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the South Side diverted from 600Sb ( near chowk
                                                mari by pass) (KM road construction work south side carriageway 1st lane
                                                at location 600SB Traffic is playing smoothly On 2nd Lane) due to Road
                                                Work
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblS1"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 12:55:51</b></span>

                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector South-II</strong><br/>
                                (Halani to Hala)<br/>
                                Ph:024-4323494
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView6"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from chandan canal bridge
                                                (KM 268 to 269) due to Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from near moro toll plaza
                                                (KM 321 to 326) due to Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from tv booster to
                                                noorpur village (KM 331 to 332) due to Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from tassi pump to nango
                                                shah (KM 333 to 335) due to Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from kunda khahi to
                                                bhiriya bypass (KM 347 to 352) due to Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from shah jamal to
                                                kandiaro toll plaza (KM 364 to 370) due to Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from salah rajper to
                                                halani (KM 375 to 380) due to Road Work
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Fog from (KM ) to (KM ). Visibility = meters</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblS2"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 12:49:30</b></span>

                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector South-III</strong>
                                <br/>
                                (Hala to Karachi New Sabzi Mandi), LEW(Sohrab Goth to Agra Taaj)<br/>
                                Ph:022-2109075
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView12"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblS3"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 12:18:24</b></span>

                            </td>
                        </tr>


                        <tr>
                            <td width="15%"><strong>Sector </strong><span class="auto-style1">N55-1</span><br/>
                                (Jamshoro - Bhan Saeedabad )<br/>
                                Ph:0254620097
                            </td>
                            <td>

                                <div>
                                    <table class="table" cellspacing="0" id="GridView22"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from 97 (KM 100) due to
                                                Incident
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblN55"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 13:45:36</b></span>

                            </td>
                        </tr>

                        <tr>
                            <td width="15%"><strong>Sector </strong><span class="auto-style1">N55-2</span><br/>
                                (Bhan Saeedabad - Ratodero )<br/>
                                Ph:074-4752944
                            </td>
                            <td>

                                <div>
                                    <table class="table" cellspacing="0" id="GridView26"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblN56" style="font-size:8pt;"></span>

                            </td>
                        </tr>

                        <tr>
                            <td rowspan="4" style="width: 15%"><strong>West Zone<br/>
                            </strong>(Hub to Uthal, Kalat to Quetta, Gwadar to Maloka)<br/>
                                Ph:081-9203974<br/>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 081-9203991
                            </td>
                            <td width="15%"><strong>Sector West-I</strong>
                                <br/>
                                (Hub to Uthal)<br/>
                                Ph:085-3361082
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="c"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblW1"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 14:16:42</b></span>

                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector West-III</strong><br/>
                                (Kalat to Quetta)<br/>
                                Ph:084-4210958
                            </td>
                            <td>
                                <div>
                                    <table class="table" cellspacing="0" id="GridView14"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the North Side diverted from Ajneeri, Mastung (KM
                                                611) due to Road Damage
                                            </td>
                                        </tr>
                                        <tr class="alert-warning">
                                            <td>Diversion : Traffic of the South Side diverted from B12 Khadkocha
                                                unknown militants have blown up the bridge (KM 603N/S kund umarani) due
                                                to Law &amp; Order Situation
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblW3"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 14:03:59</b></span>

                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector N10</strong>
                                <br/>
                                (Gawadar to Makola )<br/>
                                Ph: 0333-0666581
                            </td>
                            <td>
                                <div>
                                    <table class=" Table" cellspacing="0" id="GridView15"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>
                                <span id="lblN10"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 12:55:42</b></span>


                            </td>
                        </tr>
                        <tr>
                            <td width="15%"><strong>Sector N50</strong>
                                <br/>
                                (Kuchlak ByPass to Killasaifullah Bypass )<br/>
                                Ph: 082-3610204
                            </td>
                            <td>
                                <div>
                                    <table class=" Table" cellspacing="0" id="GridView28"
                                           style="font-size:Small;border-collapse:collapse;">
                                        <tr class="alert-success">
                                            <td>Road & Weather Clear</td>
                                        </tr>
                                    </table>
                                </div>

                                <span id="lblN50"
                                      style="font-size:8pt;">Last updated on : <b>30-Jul-26 14:29:21</b></span>
                            </td>
                        </tr>
                    </table>


                    <script type="text/javascript">
                        //
                        <
                        ![CDATA[

                        theForm.oldSubmit = theForm.submit;
                        theForm.submit = WebForm_SaveScrollPositionSubmit;

                        theForm.oldOnSubmit = theForm.onsubmit;
                        theForm.onsubmit = WebForm_SaveScrollPositionOnSubmit;
                        //]]>
                    </script>
                </form>

            </div>
        </div>

    </div>
</div>

<script>

    var rows = document.getElementById("GridView1").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView2").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView3").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView4").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView5").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView6").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView7").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView8").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView9").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>

<script>

    var rows = document.getElementById("GridView10").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView11").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView12").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView13").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView14").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView15").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView16").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView17").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>
<script>

    var rows = document.getElementById("GridView18").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>

<script>

    var rows = document.getElementById("GridView18").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>


<script>

    var rows = document.getElementById("c").getElementsByTagName("tbody")[0].getElementsByTagName("tr");

    // loops through each row
    for (i = 0; i < rows.length; i++) {
    cells = rows[i].getElementsByTagName('td');
    if (cells[0].innerHTML.search("Public Protes") >= 0)
    rows[i].className = "yellow";


}
</script>


</body>
