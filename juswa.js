// ==UserScript==
// @name         justwatchv2007v3
// @namespace    http://tampermonkey.net/
// @version      0.6
// @description  try to take over the world!
// @author       You
// @match        https://www.justwatch.com/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=justwatch.com
// @grant        none
// @run-at       document-idle
// @require      http://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js
// @require      https://gist.github.com/raw/2625891/waitForKeyElements.js
// ==/UserScript==

(function() {
    'use strict';

    // Function to create the custom window
    function createCustomWindow() {
        // Create the main container for the custom window
        const container = document.createElement('div');
        container.id = "customcontainer";
        container.style.position = 'fixed';
        container.style.top = '50%';
        container.style.left = '50%';
        container.style.transform = 'translate(-50%, -50%)';
        container.style.backgroundColor = '#fff';
        container.style.border = '1px solid #ccc';
        container.style.padding = '10px';
        container.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.3)';
        container.style.zIndex = '9999';
        container.style.backgroundColor = 'rgba(6,13,23,255)';
        container.style.width = '400px'; // Set the width of the container

        const label1 = document.createElement('label');
        label1.for = 'input1'; // Associate the label with input1
        label1.innerText = 'Title:';

        // Create the three input boxes
        const input1 = document.createElement('input');
        input1.type = 'text';
        input1.style.width = '100%';
        input1.value = document.getElementsByClassName("title-block")[0].getElementsByTagName("h1")[0].textContent.trim()
        // input1.value = document.querySelector("#base > div.jw-info-box > div > div.jw-info-box__container-content > div:nth-child(2) > div.title-block__container > div.title-block > div > h1").textContent;

        const label2 = document.createElement('label');
        label2.for = 'input2'; // Associate the label with input1
        label2.innerText = 'Which season to watch next:';

        const input2 = document.createElement('input');
        input2.type = 'text';
        input2.style.width = '100%';
        input2.value = '1';

        const label3 = document.createElement('label');
        label3.for = 'input1'; // Associate the label with input1
        label3.innerText = 'Which episode to watch next:';

        const input3 = document.createElement('input');
        input3.type = 'text';
        input3.style.width = '100%';
        input3.value = '1';

        // Create the submit button
        const submitButton = document.createElement('button');
        submitButton.innerText = 'OK';
        submitButton.style.backgroundColor = 'rgba(6,43,43,255)';
        submitButton.style.color = 'white'
        submitButton.style.border = 'none';
        submitButton.style.marginTop = '5px';
        submitButton.style.marginRight = '10px';
        submitButton.addEventListener('click', () => {
            // Get the values from the input boxes
            const value1 = input1.value;
            const value2 = input2.value;
            const value3 = input3.value;

            // Do something with the values (you can modify this part)
            //alert(`Input 1: ${value1}\nInput 2: ${value2}\nInput 3: ${value3}`);
            var data = JSON.stringify({
                       "title": value1.trim().replace(/[^a-zA-Z0-9-_ ]/gi, ''),
                       "year":document.getElementsByClassName("title-block")[0].getElementsByTagName("span")[0].textContent.trim(),
                       //"year": document.querySelector("#base > div.jw-info-box > div > div.jw-info-box__container-content > div:nth-child(2) > div.title-block__container > div.title-block > div > span").textContent.trim(),
                       "newest_season": getseason(),
                       "newest_episode": getepisode(),
                       "progress_season": value2 ? "S" + value2 : "S0",
                       "progress_episode": value3 ? "E" + String(parseInt(value3)-1) : "E0",
                       "found": false,
                       "ismovie": showdet(),
                       "url": window.location.href
                       });


            var xhr2 = new XMLHttpRequest();
            xhr2.withCredentials = true;

            xhr2.addEventListener("readystatechange", function () {
                if (this.readyState === 4) {
                    console.log(this.responseText);
                }
            });
            xhr2.open("POST", "");
            xhr2.setRequestHeader("content-type", "application/json");
            xhr2.setRequestHeader("x-apikey", "");
            xhr2.setRequestHeader("cache-control", "no-cache");
            xhr2.send(data);

            var xhr1 = new XMLHttpRequest();
            xhr1.withCredentials = true;

            xhr1.addEventListener("readystatechange", function () {
                if (this.readyState === 4) {
                    console.log(this.responseText);
                }
            });

            xhr1.open("POST", "");
            xhr1.setRequestHeader("content-type", "application/json");
            xhr1.setRequestHeader("x-apikey", "");
            xhr1.setRequestHeader("cache-control", "no-cache");
            xhr1.send(data);

            var xhr3 = new XMLHttpRequest();
            xhr3.withCredentials = true;

            xhr3.addEventListener("readystatechange", function () {
                if (this.readyState === 4) {
                    console.log(this.responseText);
                }
            });

            xhr3.open("POST", "");
            xhr3.setRequestHeader("content-type", "application/json");
            xhr3.setRequestHeader("x-apikey", "");
            xhr3.setRequestHeader("cache-control", "no-cache");
            xhr3.send(data);

            // Close the custom window
            container.remove();
        });

        const cancelButton = document.createElement('button');
        cancelButton.innerText = 'Cancel';
        cancelButton.style.backgroundColor = 'rgba(6,43,43,255)';
        cancelButton.style.color = 'white'
        cancelButton.style.border = 'none';
        cancelButton.addEventListener('click', () => {
            // Close the custom window
            container.remove();
        });

        // Append all elements to the container
        container.appendChild(label1);
        container.appendChild(input1);
        container.appendChild(document.createElement('br'));
        if (!window.location.href.includes("movie")) {
            container.appendChild(label2);
            container.appendChild(input2);
            container.appendChild(document.createElement('br'));
            container.appendChild(label3);
            container.appendChild(input3);
            container.appendChild(document.createElement('br'));
        }
        container.appendChild(submitButton);
        container.appendChild(cancelButton);

        // Append the container to the document body
        document.body.appendChild(container);
    }


    // Function to create and append the button
    function showdet() {
        return (window.location.href.includes("movie") ? true : false);
    }
    function getseason() {
        if (window.location.href.includes("tv-series") || window.location.href.includes("tv-show")) {
            return document.getElementsByClassName("episodes-item")[0].getElementsByTagName("span")[0].textContent.split(" ")[0]
            //return document.querySelector("#base > div.jw-info-box > div > div.jw-info-box__container-content > div:nth-child(2) > div:nth-child(4) > div:nth-child(4) > ul > li:nth-child(1) > div > h4 > span:nth-child(1)").textContent.split(" ")[0]
        } else {
            return "S0"
        }
    }
    function getepisode() {
        if (window.location.href.includes("tv-series") || window.location.href.includes("tv-show")) {
            return document.getElementsByClassName("episodes-item")[0].getElementsByTagName("span")[0].textContent.split(" ")[1]
            //return document.querySelector("#base > div.jw-info-box > div > div.jw-info-box__container-content > div:nth-child(2) > div:nth-child(4) > div:nth-child(4) > ul > li:nth-child(1) > div > h4 > span:nth-child(1)").textContent.split(" ")[1]
        } else {
            return "E0"
        }
    }
    function createButton() {
        var button = document.createElement('button');
        button.innerText = 'Download';

        // Apply the desired CSS styles
        button.style.backgroundColor = 'rgba(6,33,43,255)';// Greyish blue background color
        button.style.color = 'white';// White text color
        button.style.border = 'none';
        button.style.fontSize = '20px';

        button.addEventListener('click', function() {
            createCustomWindow()
        });

        return button;
    }

    // Function to check if the button exists and insert it
    function checkAndInsertButton() {
        var targetContainer = document.querySelector('.title-block div'); // Replace with the ID or selector of your target container element

        if (targetContainer && !document.querySelector('#myButton')) {
            var button = createButton();
            button.id = 'myButton';
            targetContainer.appendChild(button);
        }
    }

    function idk() {
        const myDiv = document.getElementById('customcontainer');

        document.onclick = function(e){
            if((e.target.id === 'customcontainer' || e.target.parentNode.id === 'customcontainer')){
                console.log("idk")
            } else {
                myDiv.remove();
            }
        }
    }

    // Start observing changes in the body element
    // Periodically check and insert the button
    // setInterval(checkAndInsertButton, 1000); // Adjust the interval (in milliseconds) as needed

    // Initial check and insert of the button
    // checkAndInsertButton();
    function addCustomSearchResult (jNode) {
        checkAndInsertButton();
    }
    waitForKeyElements (".title-block", addCustomSearchResult);
    waitForKeyElements ("#customcontainer", idk);
})();
