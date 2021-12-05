<?php

if ($_SERVER['REQUEST_METHOD'] == 'PUT') {
    $content = file_get_contents("php://input");
    file_put_contents('epg.xml', $content);
    echo "success";
    http_response_code(200);
    exit();
}
echo "No file provided.";
http_response_code(500);